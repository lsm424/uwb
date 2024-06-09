import socket,threading,time,os,psutil
import numpy as np
import multiprocessing as P
import hashlib,struct,pandas
global tot_packets
COMBINE_TIMEOUT = 1.0
MAPCOUNT_PARSETLV = 4
MAPCOUNT_COMBINE = 3
MAPCOUNT_PARSE = 1
tot_packets = {}
BUFFERSIZE = 10000
_types = set()
def merge(x:dict,y:dict):
    ret = {}
    for i in x:
        ret[i] = x[i]
    for i in y:
        ret[i] = ret[i] + y[i]
    return ret
def Parse_2011(data):
    maxlen = max([len(i) for i in data])
    framebuffer = np.zeros((len(data),maxlen),dtype=np.uint8)
    for i in range(len(data)):
        framebuffer[i,:len(data[i])] = np.frombuffer(data[i],np.uint8)
    流水号 = framebuffer[:,10:12] @ [1,256]
    Anchor = framebuffer[:,14:16] @ [1,256]
    uniqueAnchors = np.unique(Anchor,return_index=True)[1]
    # 之前没有声明的业务逻辑:同一个Anchor的数据总是作为一个整体进行转发,去重时同一个Anchor的数据一定是重复的
    framebuffer = framebuffer[uniqueAnchors]
    流水号 = 流水号[uniqueAnchors]
    Anchor = Anchor[uniqueAnchors]
    
    N = framebuffer[:,6:8] @ [1,256]
    N=(N-8)//6
    maxN = np.max(N)
    tagData = framebuffer[:,16:16+6*maxN].reshape((framebuffer.shape[0],-1,6),order="C")@[[1,0,0,0],[256,0,0,0],[0,1,0,0],[0,256,0,0],[0,0,1,0],[0,0,0,1]]
    anchorTagData = np.concatenate([
        np.repeat(流水号[:,None,None],tagData.shape[1],1),
        np.repeat(Anchor[:,None,None],tagData.shape[1],1),
        tagData],2)
    anchorTagData = np.concatenate([anchorTagData[i,:N[i],:] for i in range(anchorTagData.shape[0])],0)
    anchorTagData = pandas.DataFrame(anchorTagData,columns=["rolling","AnchorId","TagID","Distance","RXL","FPL"])
    return anchorTagData
def Parse_300D(data):
    # 固定长度70的帧
    framebuffer = np.concatenate([np.frombuffer(i,np.uint8)[None,:] for i in data],0)
    TagID = (framebuffer[:,10:12] @ [1,256]).astype(np.float32)
    rolling = (framebuffer[:,12:14] @ [1,256]).astype(np.float32)
    time = (framebuffer[:,14:18] @ [1,256,65536,256**3]).astype(np.float32)
    floatvalue = framebuffer[:,18:66].view(dtype=np.float32)
    heartrate = (framebuffer[:,66:68] @ [1,256]).astype(np.float32)
    value = np.concatenate([
        rolling[:,None],TagID[:,None],time[:,None],floatvalue,heartrate[:,None]
    ],1)
    uniqueTags = np.unique(TagID,return_index=True)[1]
    value=value[uniqueTags,:]
    
    return pandas.DataFrame(value,columns=[
            "rolling","TagID","time","batt",
            "pres","temp","acc_x","acc_y","acc_z",
            "gyr_x","gyr_y","gyr_z","mag_x","mag_y","mag_z","heart"])
def rolling_offset(type):
    if type == 0x300d:return 12;
    else :return 10
def task_Parse(t0,srcQueue,dstQueue):
    parsers = {
        0x2011:Parse_2011,
        0x300D:Parse_300D
    }
    outpNames = {
        0x2011:"TOF距离集中上传",
        0x300D:"传感器数据输出"
    }
    outpFiles = {i:open("%d/%s.csv"%(t0,outpNames[i]),'wb') for i in outpNames}
    titleOutputed = {i:False for i in outpFiles}
    while True:
        rolling,frames=srcQueue.get()
        classified = {}
        for i in frames:
            type = int.from_bytes(i[4:6],'little')
            if type not in classified:classified[type]=[]
            classified[type].append(i)
        results = {}
        for i in parsers:
            if i in classified:
                from typing import Dict
                results:Dict[int,pandas.DataFrame]
                results[i]=parsers[i](classified[i])
                results[i].to_csv(outpFiles[i], header=not titleOutputed[i], index=False);titleOutputed[i]=True
                outpFiles[i].flush()
        # print(rolling,len(frames))
def task_combine(srcQueue,dstQueue):
    buffer = {}
    while True:
        rolling,framedata=srcQueue.get()
        if rolling not in buffer:
            buffer[rolling] = (time.time(),[framedata])
        else:buffer[rolling][1].append(framedata)
        finished_rolls = [i for i in buffer if time.time() > buffer[i][0]+COMBINE_TIMEOUT]
        for i in finished_rolls:
            dstQueue.put((i,buffer[i][1]))
            del buffer[i]
def task_recv(srcQueue,destQueues):
    buffer = {}
    while True:
        d,src=srcQueue.get()
        if src not in buffer:buffer[src]=np.zeros((0,),np.uint8)
        d=np.concatenate([buffer[src],np.frombuffer(d,np.uint8)])
        # 找帧头
        headerPos = np.where(np.logical_and(d[:-5] == 0xF5,d[1:-4] == 0x5a))[0]
        lengths = d[headerPos+2]+d[headerPos+3]*256
        tailPos = headerPos +lengths +4
        validFrames = np.logical_and(tailPos < len(d) ,lengths<4096)
        headerPos=headerPos[validFrames]
        lengths=lengths[validFrames]
        tailPos=tailPos[validFrames]
        
        types = d[headerPos+4]+d[headerPos+5]*256
        offset = headerPos + np.array([rolling_offset(i) for i in types])
        rollings = d[offset]+d[offset+1]*256
        frames = [d[headerPos[i]:tailPos[i]] for i in range(len(types))]
        
        buffer[src]=d[tailPos[-1]:]
        for i in range(len(types)):
            destQueues[rollings[i]%MAPCOUNT_COMBINE].put((int(rollings[i]),frames[i].tobytes()))
        for i in rollings:
            if i not in tot_packets:tot_packets[i]=0
            tot_packets[i] += 1
def recvUDP(t0,dest):
    def Hash(b):
        hash_object = hashlib.sha256()
        hash_object.update(b)
        return int.from_bytes(hash_object.digest())
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
    s.bind(("0.0.0.0",9999))
    s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1000000)
    mapping = {}
    files = {}
    while True:
        d,_src = s.recvfrom(65536)
        src = _src[0].encode("ASCII")+_src[1].to_bytes(2)
        if src not in mapping:
            mapping[src]= Hash(src)%MAPCOUNT_PARSETLV
            files[src] = open("%d/%d_%s_%d.bin"%(t0,t0,_src[0],_src[1]),"wb")
        dest[mapping[src]].put((d,src))
        files[src].write(d)
        files[src].flush()
        

def main():
    t0=time.time()
    os.mkdir("%d"%t0)
    parsetlv_ibuf = [P.Queue() for i in range(MAPCOUNT_PARSETLV)]
    combinetlv_ibuf = [P.Queue() for i in range(MAPCOUNT_COMBINE)]
    combined_buf = P.Queue()
    final_buf = P.Queue()
    
    parsetlv_processes = [P.Process(target=task_recv,args=(parsetlv_ibuf[i],combinetlv_ibuf)) for i in range(MAPCOUNT_PARSETLV)]
    combinetlv_processes = [P.Process(target=task_combine,args=(combinetlv_ibuf[i],combined_buf)) for i in range(MAPCOUNT_COMBINE)]
    parse_process = P.Process(target=task_Parse,args=(t0,combined_buf,final_buf))
    
    receiveUDP_process = P.Process(target=recvUDP,args=(t0,parsetlv_ibuf,));
    for i in parsetlv_processes:i.start()
    for i in combinetlv_processes:i.start()
    parse_process.start()
    receiveUDP_process.start()
    
    pid = os.getpid()
    p = psutil.Process(pid)
    print(pid)
    while True:
        time.sleep(1)
        
        print(*[i.qsize() for i in parsetlv_ibuf+combinetlv_ibuf+[combined_buf]])
if __name__ == "__main__":
    main()