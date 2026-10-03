main:
	li	$v0, 11
	li	$a0, ';'
	syscall

	li	$t0, 42

	# this is a beq $t0, $t0 instruction with an offset
	# of +4 (which is after the last instruction)
	.word	0x11080004

	li	$v0, 10
	syscall
