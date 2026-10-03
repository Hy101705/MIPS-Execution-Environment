main:
	# print -1 (0xffffffff)
	lui	$t0, 0xffff		# upper 16 bits
	ori	$t1, $t0, 0xffff	# lower 16 bits
	addi	$a0, $t1, 0
	li	$v0, 1
	syscall

	# putchar('\n')
	li	$v0, 11
	li	$a0, '\n'
	syscall

	# print 0xdeadbeef
	lui	$t1, 0xdead		# upper 16 bits
	ori	$t1, $t1, 0xbeef	# lower 16 bits
	addi	$a0, $t1, 0
	li	$v0, 1
	syscall

	# putchar('\n')
	li	$v0, 11
	li	$a0, '\n'
	syscall

	# putchar('*');
	li	$t0, 42
	addi	$a0, $t0, 0
	syscall

	# print 42 | 7 = 47
	ori	$a0, $t0, 7
	li	$v0, 1
	syscall

	# putchar('\n')
	li	$v0, 11
	li	$a0, '\n'
	syscall

	li	$v0, 10
	syscall
