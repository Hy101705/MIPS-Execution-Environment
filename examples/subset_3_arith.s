main:
	li	$t1, 0xabcddcba
	li	$t2, 0xf00df00d
	addu	$t0, $t1, $t2
	move	$a0, $t0
	li	$v0, 1
	syscall

	li	$a0, ' '
	li	$v0, 11
	syscall

	li	$t3, 0x5f1
	mul	$a0, $t0, $t3
	li	$v0, 1
	syscall

	li	$a0, '\n'
	li	$v0, 11
	syscall

	li	$v0, 10
	syscall
