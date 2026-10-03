main:
	li	$t0, 42
	la	$t1, answer
	sb	$t0, 0($t1)		# store 42 in byte at address labelled answer

	lb	$a0, 0($t1)		# load $a0 from same address

	li	$v0, 1			# print $a0 which will nows contain 42
	syscall

	li	$a0, '\n'		# print '\n'
	li	$v0, 11
	syscall

	li	$v0, 10
	syscall

	.data
answer:
	.space 1			# set aside 1 byte and associate label answer with its address
