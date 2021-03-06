/*

Simple character device file. Creates a readonly char 
device that tells how many times you have accessed
dev file.

*/

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/uaccess.h> 	/* For put_user */

/************ 	PROTOTYPE 	**************/

int init_module(void);
void cleanup_module(void);
static int device_open(struct inode *, struct file *);
static int device_release(struct inode *, struct file *);
static ssize_t device_read(struct file *, char *, size_t, loff_t *);
static ssize_t device_write(struct file *, const char *, size_t, loff_t * );

#define DEVICE_NAME 	"my_chardev"	/* Create a device with this name in /proc/devices */
#define BUF_LEN		255		/* Max lenght of msg from device */



/************ 	GLOBAL VARIABLES 	**************/

/*
Note : Here global variables are declared static 
	 so that they will be accessable through 
	 this file only
*/

static int Major;		/* Major number assigned to our device driver */
static int Device_open = 0;	/* Flag to check if device is open already */
				/* to prevent multiple access to device    */
static char msg[BUF_LEN];	/* To print device Message */
static char *msg_ptr;

static struct file_operations fops ={
	.read	=device_read,
	.write	=device_write,
	.open	=device_open,
	.release=device_release
};




/************ 	LOCAL FUNCTIONS 	**************/


/*
function_name 	: init_module()
description	: This function will be called when 
		  when module in loaded vai insmod
*/

int init_module(void)
{
	/* Acquire Major number for our device */
	Major = register_chrdev(0, DEVICE_NAME, &fops);
	if( 0 > Major)
	{
		printk(KERN_ALERT "Registration failed :  my_chardev\n");
		return Major;
	}

	printk(KERN_INFO "Dev file created : mknod /dev/%s c %d 0 .\n",DEVICE_NAME,Major);
	return 0;
} 



/*
function_name   : cleanup_module()
description     : This function will be called when 
                  when module in un-loaded vai rmmod
*/
void cleanup_module(void)
{
	unregister_chrdev(Major,DEVICE_NAME);
}



/*
function_name   : device_open()
description     : This function will be called when 
                  when process opens device file
		  eg: cat /dev/my_chardev
*/
static int device_open(struct inode *inode, struct file *file)
{
	static int counter = 0;
	
	if(Device_open)
		return -EBUSY;

	Device_open++;
	sprintf(msg,"You have opened this dev file %d times",counter++);
	msg_ptr = msg;
	try_module_get(THIS_MODULE);
	return 0;
}



/*
function_name   : device_close()
description     : This function will be called when 
                  when process close device file
*/
static int device_release(struct inode *inode, struct file *file)
{
	Device_open--; 		/* Free this flag after use for next caller */
	module_put(THIS_MODULE);
	return 0;
}



/*
function_name   : device_read()
description     : This function should be called by process 
		  after opening device file to read from that
		  device file.
*/
static ssize_t device_read(struct file *file, char *buffer,\ 
				size_t length, loff_t *offset)
{
	/* Bytes actually written to the buffer */
	int byte_read=0; 
	
	if(0 == *msg_ptr)
		return 0; /* End of msg signified by '0' */

		/* 
		 * The buffer is in the user data segment, not the kernel 
		 * segment so "*" assignment won't work.  We have to use 
		 * put_user which copies data from the kernel data segment to
		 * the user data segment. 
		 */
	while(length  && *msg_ptr)
	{
		put_user(*(msg_ptr++),(buffer++));
		length--;
		byte_read++;
	}

	/* Return number of bytes put into buffer */
	return byte_read;
}



/*
function_name   : device_read()
description     : This function should be called by process 
                  after opening device file to write to dev
		  file : echo "Hello_world" > /dev/my_chardev
*/
static ssize_t device_write(struct file *file, const char *buff, size_t len, loff_t *off)
{
	printk(KERN_ALERT "Sorry this operation is not supported.\n");
	return -EINVAL;
}

