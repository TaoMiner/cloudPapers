ubuntu 16.04

anaconda在ubuntu下并没有链接对应的tk文字管理器，因此tkinter在linux下界面会很丑，尤其是ubuntu。解决方案有二：
1. 替换掉~/anaconda/lib/libtk8.6.so为系统的/usr/lib/x86_64-linux-gnu/libtk8.6.so，但注意系统的python版本，要与anaconda的匹配。
2. 每次使用sudo python启动文件，这样其实就是使用系统的python，但可能没有装tkinter。先切换系统python版本到3.5，https://blog.csdn.net/fang_chuan/article/details/60958329。

列出所有python版本
ls /usr/bin/python*
设置替换python
update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
update-alternatives --install /usr/bin/python python /usr/bin/python3.5 2
此时可以查看默认python版本为python3.5，但可能没有pip，故安装pip
sudo apt-get install python3-pip
pip版本太老，升级
pip3 install --upgrade pip
安装tkinter for python3
apt-get install python3-tk
此时可以正常启动tkinter，并且界面字体正常。