main:
	la	$t0, my_array

	# print address of my_arrray
	move	$a0, $t0
	li	$v0, 1
	syscall

	# print word at my_array
	lw	$a0, ($t0)
	syscall

	# putchar('\n');
	li	$v0, 11
	li	$a0, '\n'
	syscall

	addiu	$t0, $t0, 2

	# unaligned load: this should crash!
	lw	$a0, ($t0)

	li	$v0, 1
	syscall

	li	$v0, 10
	syscall


	.data
my_array:
	.byte	42, 43, 44, 45, 47, 48, 49, 50
