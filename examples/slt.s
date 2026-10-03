	# A test involving slt with various values

main:
	li	$t0, 6
	li	$t1, 8

	li	$v0, 1

	slt	$a0, $t0, $t1
	syscall			# should be 1

	li	$t0, 7
	slt	$a0, $t0, $t1
	syscall			# should be 1

	li	$t0, 8
	slt	$a0, $t0, $t1
	syscall			# should be 0

	li	$t0, 9
	slt	$a0, $t0, $t1
	syscall			# should be 0

	li	$t0, -1
	slt	$a0, $t0, $t1
	syscall			# should be 1

	li	$t0, -1234
	slt	$a0, $t0, $t1
	syscall			# should be 1

	li	$t0, -2147483648
	slt	$a0, $t0, $t1
	syscall			# should be 1

	li	$t0, 2147483647
	slt	$a0, $t0, $t1
	syscall			# should be 0

	li	$t1, -4
	li	$t0, -4
	slt	$a0, $t0, $t1
	syscall			# should be 0

	li	$t1, -4
	li	$t0, -7
	slt	$a0, $t0, $t1
	syscall			# should be 1

	li	$v0, 11
	li	$a0, '\n'
	syscall

	li	$v0, 10
	syscall
