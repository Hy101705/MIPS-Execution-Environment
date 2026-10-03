main:
	li	$t0, -2147483645
	li	$t1, -100
	add	$t2, $t0, $t1

	li	$v0, 10
	syscall
