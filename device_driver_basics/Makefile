#
#Author 	: Aditya Kasar
#
#Description 	: This is main makefile which will be used 
#		  to compile device driver module, also 
#		  also termed as loadable kernel module. 
#

obj-m +=src/hello.o

build_module:
		make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
clean_module:
		make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
