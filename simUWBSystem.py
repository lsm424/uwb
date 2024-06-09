import socket
import numpy as np
from abc import abstractmethod,ABC
# 1个进程模拟1个项目
import time,json
import math,random
import struct,crcmod
import os
anchorCount = 6
tagCount = 1 # 3.5MB/s
np.random.seed(666)
random.seed(666)

_XMODEM = crcmod.predefined.Crc("XMODEM")
def CRC16_CCITT(data):
    a=_XMODEM.copy()
    a.update(data)
    return a.crcValue
def CALC_DIST(x,y):
    temp = math.sqrt((x[0]-y[0])**2+(x[1]-y[1])**2+(x[2]-y[2])**2)+ np.random.normal()*0.04
    return 0 if temp<0.01 else temp
FSPS = 20;
# 虚拟UWB定位基站输出数据
class coordGenerator(ABC):
    #模拟标签的周期性运动
    def __init__(self,period=60*20,**kwargs):
        self._phase=0;
        self.phase=0.0;
        self.period=period;
        self._phase=random.random()*period;
    def step(self):# 20Hz调用 更新状态
        self._phase=(self._phase+1)%self.period;
        self.phase=self._phase/self.period;
        self.coord = (0.0,0.0,0.0)
class CirclecoordGenerator(coordGenerator):
    #模拟标签画圆运动
    def __init__(self,center=None,radius=10.0,**kwargs):
        super().__init__(**kwargs)
        self.center=(0.0,0.0,0.0)if center is None else center
        self.radius=radius
    def step(self):
        super().step()
        self.coord = (
            math.sin(2*math.pi*self.phase)*self.radius+self.center[0],
            math.cos(2*math.pi*self.phase)*self.radius+self.center[1],
            self.center[2]
        );
class IMUGenerator:
    #模拟标签各传感器示数
    def __init__(self,**kwargs):
        self.time=0;
        self.rolling=0;
        self.batt = 4.0 + np.random.normal()*0.07;
        self.pres = 101325.0 + np.random.normal()*100.0;
        self.temp = 25 + np.random.normal()*1.0;
        self.acc = [i + np.random.normal()*0.1 for i in (9.8,0.0,0.0)];
        self.gyr = [i + np.random.normal()*0.1 for i in (0.0,0.0,0.0)];
        self.mag = [i + np.random.normal()*0.1 for i in (0.0,140.0,0.0)];
    def step(self):
        self.rolling = (self.rolling+1)%(2**32);
        self.time = (self.time+50)%(2**32);
        self.batt = 1000.0*(4.0 + np.random.normal()*0.2);
        self.pres = 101325.0 +np.random.normal()*100.0;
        self.temp = 25 +np.random.normal()*1.0;
        self.acc = [i + np.random.normal()*0.1 for i in (9.8,0.0,0.0)];
        self.gyr = [i + np.random.normal()*0.1 for i in (0.0,0.0,0.0)];
        self.mag = [i + np.random.normal()*0.1 for i in (0.0,140.0,0.0)];
class UWBModule(ABC):
    # UWB定位模块具有编号和位置
    def __init__(self,**kwargs):
        self.ID = None
        self.coord = None
    @abstractmethod
    def step(self):
        pass
class Tag(UWBModule):
    # 标签装有各种传感器
    # 标签编号取值范围:[0x8000,0xffff)
    # 标签的位置在移动，定位系统需要输出标签的位置。
    def __init__(self,**kwargs):
        self.coordGenerator=CirclecoordGenerator(**kwargs)
        self.imuGenerator = IMUGenerator(**kwargs);
        self.rolling = 0;
        self.ID = kwargs["ID"] if "ID" in kwargs else random.randint(32768,65534);
        self.coord = self.coordGenerator.center
        self.relatedModule=[];
        self.relatedModulePLR = [];
    def step(self):# 20Hz调用 更新状态
        self.coordGenerator.step()# 计算虚拟标签位置
        self.imuGenerator.step()#计算虚拟标签传感器读数
        self.coord = self.coordGenerator.coord;
        self.rolling = self.rolling +1;


    def GetIMUData(self, anchorID):
        # 生成UWB TLV 0x300d 帧：
        data = struct.pack("=HHHHHHHLffffffffffffH",
            0x5af5,
            # 帧头
            0x42,  # 帧总长度
            0x300d,  # Type
            0x3C,  # 数据长度
            anchorID, self.ID,  #  Source ID Tag ID
            self.imuGenerator.rolling % 65536,  # 文档中结构体各数据项
            self.imuGenerator.time, # 文档中结构体各数据项
            self.imuGenerator.batt, # 文档中结构体各数据项
            self.imuGenerator.pres, # 文档中结构体各数据项
            self.imuGenerator.temp, # 文档中结构体各数据项
            *self.imuGenerator.acc,
            # float[3]  # 文档中结构体各数据项
            *self.imuGenerator.gyr,
            # float[3]  # 文档中结构体各数据项
            *self.imuGenerator.mag,  # float[3]  # 文档中结构体各数据项
            666
        )
        data=data+struct.pack("H",CRC16_CCITT(data));
        return data
class Anchor(UWBModule):
    def __init__(self,relatedModule,relatedModulePLR=None,coord=None,**kwargs):
        self.ID = kwargs["ID"] if "ID" in kwargs else random.randint(1,32767);
        self.relatedModule=relatedModule[:];
        self.relatedModulePLR = [0.0 for i in range(len(relatedModule))] if relatedModulePLR is None else relatedModulePLR[:]
        self.coord=coord if coord is not None else (0.0,0.0,0.0);
        self.tagID= None
        self.tagdistance= None
        self.tagRXL=None
        self.tagFPL=None
        self.rolling=0;
    def step(self):# 20Hz调用,输出TLV数据
        gotModule = [];
        for i in range(len(self.relatedModule)):
            if self.relatedModulePLR[i]<np.random.random():# and self.relatedModule[i].ID > self.ID:
                gotModule.append(self.relatedModule[i])
        #模拟测距，测距有一定的丢包率
        self.tagID= [i.ID for i in gotModule]
        self.tagdistance= [CALC_DIST(self.coord,i.coord) for i in gotModule]
        self.tagRXL= [-65 for i in gotModule]
        self.tagFPL= [-67 for i in gotModule]
        self.rolling = self.rolling +1;
    
    def GetTOFData(self):
        #TODO
        # 基站可以上报出自己联通的所有标签
        # 基站可以上报出自己联通的所有基站跟标签的测距结果
        if(self.tagID is None):return b""
        temp=[];
        for i in range(len(self.tagID)):
            temp = temp + [self.tagID[i],int(100*self.tagdistance[i])%65536,int(-self.tagRXL[i])%256,int(-self.tagFPL[i])%256];
        data = struct.pack("HHHHHHHH"+"HHBB"*len(self.tagID),
                          0x5af5,#帧头
                          14+len(self.tagID)*6,# 帧总长度
                          0x2011,# Type
                          8+len(self.tagID)*6,# 数据长度
                          self.ID,self.rolling%65536,0xB1,self.ID,#  Source ID Tag ID
                          *temp
                          )
        data=data+struct.pack("H",CRC16_CCITT(data));
        return data
    def GetTLVData(self):
        if(self.tagID is None):return b""
        data=b'';
        data=data+self.GetTOFData()
        for i in self.relatedModule:
            if(type(i) is Anchor):
                data=data+i.GetTOFData()
            if(type(i) is Tag):
                data=data+i.GetIMUData(self.ID)
        return data

        
def MakeNetwork(anchorCount:int,tagCount:int,GatewayCount:int,MutualSlot=12,taganchorSlot=6,tagSlot=15,PLR=0.0):
    Anchors = [];
    Tags = [];
    # 建立基站
    anchorlinecount = math.ceil(math.sqrt(anchorCount));
    taglinecount = math.ceil(math.sqrt(tagCount));
    X=math.ceil(taglinecount/anchorlinecount)*10.0;
    X=10.0 if X<10 else X;
    anchorIDs =np.random.choice(32768, anchorCount, replace=False)
    j=np.random.choice(anchorCount, anchorCount, replace=False)
    for i in range(anchorCount):
        Anchors.append(Anchor([],coord=[100.0*random.random(),100.0*random.random(),0],ID=anchorIDs[i]))
    # 建立互测距连接
    for i in range(len(Anchors)):
        delta = range(i-(MutualSlot//2),i+(MutualSlot//2));
        for j in delta:
            if(i==j):continue;
            try:
                I=Anchors[i%anchorCount];
                J=Anchors[j%anchorCount];
            except IndexError:continue;
            if(I in J.relatedModule or J in I.relatedModule):continue;
            if(len([x for x in I.relatedModule if type(x) is Anchor]) < MutualSlot):
                if(len([x for x in J.relatedModule if type(x) is Anchor]) < MutualSlot):
                    I.relatedModule.append(J);
                    J.relatedModule.append(I);
                    temp = random.random()
                    # if(temp > 0.9):\
                    #     temp=0.75;
                    # elif(temp > 0.7):
                    #     temp=0.35;
                    # else:
                    temp = 0;
                    I.relatedModulePLR.append(temp);
                    J.relatedModulePLR.append(temp);
                else:continue;
            else:break;
        assert(len(I.relatedModule)>=3);
    # 建立标签
    tagIDs =[32768+x for x in np.random.choice(32768, tagCount, replace=False)]
    j=np.random.choice(tagCount, tagCount, replace=False)
    for i in range(tagCount):
        Tags.append(Tag(center=[X*(j[i]//anchorlinecount),X*(j[i]%anchorlinecount),0],radius=8.0,ID=tagIDs[i]))
    
    # 建立测距连接
    for i in range(len(Tags)):
        delta = range(round(i*anchorCount/tagCount-(taganchorSlot//2)),round(i*anchorCount/tagCount+(taganchorSlot//2)));
        for j in delta:
            try:
                I=Tags[i%tagCount];
                J=Anchors[j%anchorCount];
            except IndexError:continue;
            if(I in J.relatedModule or J in I.relatedModule):continue;
            if(len([x for x in I.relatedModule if type(x) is Anchor]) < taganchorSlot):
                if(len([x for x in J.relatedModule if type(x) is Tag]) < tagSlot):
                    I.relatedModule.append(J);
                    J.relatedModule.append(I);
                    temp = random.random()
                    # if(temp > 0.9):
                    #     temp=0.75;
                    # elif(temp > 0.8):
                    #     temp=0.35;
                    # else:
                    temp = 0;
                    I.relatedModulePLR.append(temp);
                    J.relatedModulePLR.append(temp);
                else:continue;
            else:break;
        assert(len(I.relatedModule)>=4);
        N=0;tempX=0.0;tempY=0.0;
        for j in I.relatedModule:
            tempX = tempX + j.coord[0] ;
            tempY = tempY + j.coord[1] ;
            N=N+1;
        I.coordGenerator.center[0]=tempX/N+ 20*random.random();
        I.coordGenerator.center[1]=tempY/N+ 20*random.random();
        I.coordGenerator.center[2]=0;
    # 建立网关Anchor列表
    
    GatewayedAnc = set();
    GatewayedTag = set();
    Gateway = Anchors[::(anchorCount//GatewayCount)]
    for i in Gateway:
        if(type(i) is Anchor):GatewayedAnc.add(i);
        for j in i.relatedModule:
            if(type(j) is Anchor):GatewayedAnc.add(j);
            if(type(j) is Tag):GatewayedTag.add(j);
    assert(len(GatewayedAnc) == anchorCount)
    return (Anchors,Tags,Gateway)

GatewayCount = anchorCount
(anchors,tags,gateways)=MakeNetwork(anchorCount,tagCount,GatewayCount)
for i in anchors:
	for j in i.relatedModule:
		if(i.ID < 32768 and j.ID < 32768 and i!=j):
			print(
                "通信成功率",
				"%04X"%i.ID,
				"%04X"%j.ID,
				i.relatedModulePLR[i.relatedModule.index(j)],
                flush=True
			)


GatewayCount=len(gateways)
sock = [socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP) for i in range(GatewayCount)]
tinit=time.time()
t0=tinit;
for i in anchors:
    print({
        "ID":int(i.ID),
        "X":i.coord[0] ,
        "Y":i.coord[1] ,
        "Z":i.coord[2] 
    },flush=True)
for i in tags:
    print({
        "ID":int(i.ID),
        "X":i.coord[0] ,
        "Y":i.coord[1] ,
        "Z":i.coord[2] 
    },flush=True)
try:
    N=0;
    while True:
        for tag in tags:tag.step()
        for anchor in anchors:anchor.step()
        data=b'';
        # 分别上报
        for i in range(len(gateways)):
            anchor=gateways[i];
            data=anchor.GetTLVData();
            while(len(data)>0):
                sock[i].sendto(data[:1024],("127.0.0.1",9999))
                data=data[1024:]
        while(time.time()<t0):
            time.sleep(0.01)
        t0=t0+0.05;
        N=N+1;
        try:
            freq = N/(time.time()-tinit)
        except BaseException as e:
            continue
        print("实际发送频率",freq)
except KeyboardInterrupt:
    for i in sock:i.close();
    
