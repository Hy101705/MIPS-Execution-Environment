main:
	la	$t0, my_byte - 7
	lb	$a0, 7($t0)

	li	$v0, 1
	syscall

	li	$v0, 11
	li	$a0, '\n'
	syscall

	li	$v0, 10
	syscall

	.data
my_byte:
	.byte	42
