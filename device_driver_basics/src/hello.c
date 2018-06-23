/*
* Author 	: Aditya Kasar
*
* Description 	: Hello.c | We will start our learning with this 
*		  simple program which is suppose to print 
*		  "Hello World" when we insmod hello.ko
*		  and "Have a Nice Day." when we do rmmod hello.ko
*/

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>

int __init hello_init()
{
	printk(KERN_INFO "Hello World\n");
	return 0;
}

int __exit hello_exit()
{
	printk(KERN_INFO "Have a Nice Day.\n");
	return 0;
}

/*
* Note : 	#include <linux/init.h> is need module_init() and 
* 		module_exit().
*/

module_init(hello_init);
module_exit(hello_exit);


MODULE_LICENSE("GPL");
MODULE_AUTHOR("Aditya Kasar");
MODULE_DESCRIPTION("Simple device driver to print msg on inserting and removing driver module");
