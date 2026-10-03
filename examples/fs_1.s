	DATA_LEN = 24
	FLAGS_WRITE_ONLY = 1
	FLAGS_READ_ONLY = 0

main:
	la	$a0, path
	li	$a1, FLAGS_WRITE_ONLY
	li	$v0, 13
	syscall
	move	$t0, $v0

	move	$a0, $t0
	la	$a1, my_data
	li	$a2, 12
	li	$v0, 14 # try read...
	syscall
	li	$v0, 15
	syscall
	addu	$a1, $a1, $v0
	li	$v0, 15
	syscall		# do another write

	la	$a0, path
	li	$a1, FLAGS_READ_ONLY
	li	$v0, 13
	syscall
	move	$t1, $v0

loop_read:
	move	$a0, $t1
	la	$a1, read_buf
	li	$a2, 1
	li	$v0, 14
	syscall
	bne	$v0, 1, exit

	li	$v0, 11
	lb	$a0, read_buf
	syscall

	b	loop_read

exit:
	li	$v0, 10
	syscall

	.data
path:
	.asciiz	"my_data.txt"
read_buf:
	.space	1
my_data:
	.ascii	"my super important data!"
