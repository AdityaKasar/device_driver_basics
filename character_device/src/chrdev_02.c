
/*

Author : Aditya Vijay Kasar

-------------------
Education Material 
-------------------
Desing of a character device driver.
Here our resource is array in kerenl space.
we are also using semaphore locks for resource array
to prevent dead-locks.
*/

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/cdev.h>
#include <linux/fs.h> 		/* for fops */
#include <linux/semaphore.h>
#include <linux/uaccess.h>

/********** PROTOTYPE **********/

static int Major;

static int device_open(struct inode *, struct file *);
static int device_release(struct inode *, struct file *);
static ssize_t device_read(struct file *, char *, size_t , loff_t *);
static ssize_t device_write(struct file *, const char *, size_t, loff_t *);


struct device{
	char array[100];
	struct semaphore sem;	
}char_arr;


/*      
cdev structure is used by kernel to keep track 
of all the character devices 
*/
struct cdev *kernel_cdev;


/* 
If the alloc_chrdev_region succeeds then the dev_no 
variable will have the combination major number that 
the kernel has allocated to your driver and the first 
minor number that we had selected. 
*/
dev_t devno;


/*
The structure is basically a set of function pointers 
left column  -> name of the operation that we want to support 
right column -> is the name of the function that will implement the operation.

So when kernel wants to read from your device, it will 
get the pointer to function that will do the read 
operation from the file_operation structure.
*/
static struct file_operations fops={
	.read	= device_read,
	.write	= device_write,
	.open	= device_open,
	.release= device_release
};



int init_module(void)
{

	int ret;

	/*
	int alloc_chrdev_region(dev_t *dev, unsigned int firstminor,unsigned int count, char *name);
	
	The arguments being passed to the function are
	dev -> 		The dev_t variable type,which will get the 
			   major number that the kernel allocates.
	firstminor -> 	The first minor number in case you 
			   are looking for a series of minor numbers for your driver.
	count -> 	The number of contiguous set of major 
			   numbers that you want to be allocated.
	name -> 	Name of your device that should be associated 
			   with the major numbers. The same name will appear in /proc/devices.
	*/
	
	ret = alloc_chrdev_region(&devno,0,1,"test_chrdev_02");
	if(0 > ret)
	{
		printk(KERN_ALERT "Major number allocation failed.\n");
		return ret;
	}
	
	/* To extract the major number from the dev_no we can use the macro MAJOR */	
	Major = MAJOR(devno);
	printk(KERN_INFO "Major number : %d",Major);

	/*
	Note :

	If you were allocating the major number statically, 
	then we would need to convert the integer number to 
	dev_t format by combining it with the corresponding 
	minor number which is done by the macro MKDEV.
	
	MKDEV takes two integer numbers as input, Major number and 
	minor number, and converts them into one dev_t type number.
	Where "dev_no" is a variable of type dev_t. 
	*/
	
	devno = MKDEV(Major,0);
	

	
	/*This will initiallise stand alone "kernel_cdev" cdev structure at runtime */
	
	kernel_cdev=cdev_alloc();
	kernel_cdev->ops	= &fops;
	kernel_cdev->owner	= THIS_MODULE;


	/* 
	Inform kernel about cdev struct using cdev_add()
	int cdev_add(struct cdev *dev, dev_t num, unsigned int count);
	dev: is the cdev structure that we have setup 
	num: is the dev_t. 
	count: The number of number of device numbers that are associated with this cdev structure.
	*/
	ret = cdev_add(kernel_cdev,devno,1);
	if(0 > ret)
	{
		printk(KERN_ALERT "Unable to add cdev.\n");
		return ret;
	}


	/*Initialise device semaphore */
//	sema_init(&char_arr.sem,1);

	return 0;
}



void clean_module(void)
{
	/*
	delete the cdev structure using the call cdev_del
	void cdev_del(struct cdev *dev);
	*/
	cdev_del(kernel_cdev);

	/*
	Then unregister the device using

	void unregister_chrdev_region(dev_t first, unsigned int count);
	first: first dev_t number of a contagious set of drivers that we want to unregister.
	count: The number of drivers to be unregistered. 
	*/
	unregister_chrdev_region(devno,1);
}



static int device_open(struct inode *inode, struct file *file)
{
	/*
	Hold the semaphore so that only one process 
	is allowed to open the device at a given time
	*/
	down(&char_arr.sem);
	return 0;
}



static int device_release(struct inode *inode, struct file *file)
{
	/* Release the semaphore hold during device_open()*/

	up(&char_arr.sem);
	return 0;
}



/*
device_read() takes following pointers
file 	-> file_operation structure
buf	-> buffer into which data from device will be read into
len 	-> number of bytes of data to be trasnfere into buffer
off	-> current possition or offset being read in the file
*/
static ssize_t device_read(struct file *file, char *buf, size_t len, loff_t *off)
{

/*
In our implementation of read, we need to put the data 
in our device, i.e. the array, which is the kernel space to the user space
so we will make use of copy_to_user().
Returns the number of bytes it could not read from the "len" number of bytes requested for
*/
	unsigned long int ret;
	ret = copy_to_user(buf,char_arr.array,len);
}



static ssize_t device_write(struct file *file, const char *buf, size_t len, loff_t *off)
{
	/* copy_from_user() copy data from user space to kernel space */
        unsigned long int ret;
        ret = copy_from_user(char_arr.array,buf,len);
}



MODULE_LICENSE("GPL");





























