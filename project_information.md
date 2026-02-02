# Project Information
```
1.项目管理文档地址
https://doc.weixin.qq.com/smartsheet/s3_AVMAkgYOANUCNZ3tAkidcTt21bJtT?scode=ACcAjwdIAAw58PsmuoAVMAkgYOANU&tab=t3VM7H&viewId=vo9GZm
2.    映悦AI-演示环境
http://115.190.248.65:9080/
admin    Admin123!
3.    映悦AI-开发环境
http://115.190.248.65:9081/
admin    Admin123!
4    数据库访问地址
115.190.248.65:3307
5.    代码仓库访问地址
https://gitee.com/yuezhi-ai/yingyueai-web
https://gitee.com/yuezhi-ai/yingyueai-python


@耿庆慧    项目管理、素材管理
@王振辉     公共接口、视频管理
@周乔        分集管理、分镜管理
@李亚杰    分镜管理、视频管理


@李旋   项目管理、分镜管理、视频管理
@王世强   剧本管理、分集管理、素材管理
```

# coze
```
pat_XlSsLvlYMhF2wChKAtOclGmEkSzIf0Oy06McWxWCC7oXIxPhHBKzfIPTEd8Tuj7K
```

# agent和现有功能集成梳理
```
1.输入一句话
	1.创建为一个项目（现有工程中的项目）--创建项目接口调用

2.扩展成剧本  --创建剧本接口调用
	2.1.只有一集 --创建分集接口调用

3.根据剧本拆分成分镜，包含多个，一个2-3s
4.生成每个分镜的首zhen图（为了保证视频的一致性）
5.生成每个分镜的视频
6.拼接每个分镜的视频为一个完整的视频
7.配音
8.剪辑或上线


https://zhuanlan.zhihu.com/p/1939028616416597529

https://www.zhihu.com/question/13259814161/answer/1911544194079631280

a0669ac1-14c6-45ca-bb92-03dc3e7fbddd

doubao-seedance-1-5-pro-251215
```