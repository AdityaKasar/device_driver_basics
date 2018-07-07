#
#Author 	: Aditya Kasar
#
#Description 	: This is main makefile which will be used 
#		  to compile device driver module, also 
#		  also termed as loadable kernel module. 
#
CONFIG_MODULE_SIG=n
#obj-m +=src/chrdev_01.o
obj-m +=src/chrdev_02.o

build_module:
		make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
clean_module:
		make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
