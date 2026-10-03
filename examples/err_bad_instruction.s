main:
	li	$v0, 11
	li	$a0, '|'
	syscall

	# This is not a valid instruction!
	.word 0xaa582801

	li	$v0, 10
	syscall
