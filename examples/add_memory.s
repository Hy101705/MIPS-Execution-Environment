main:
	li	$t0, 17
	la	$t1, x
	sw	$t0, 0($t1)		# x = 17;

	li	$t0, 25
	la	$t1, y
	sw	$t0, 0($t1)		# y = 25;

	la	$t0, x
	lw	$t1, 0($t0)
	la	$t0, y
	lw	$t2, 0($t0)
	add	$t3, $t1, $t2
	la	$t0, z
	sw	$t3, 0($t0)		# z = x + y;

	li	$v0, 1			# syscall 1: print_int
	la	$t0, z			#
	lw	$a0, 0($t0)		#
	syscall				# printf("%d", z);

	li	$v0, 11			# syscall 11: print_char
	li	$a0, '\n'		#
	syscall				# putchar('\n');

	li	$v0, 10
	syscall

	.data
x:
	.space	4
y:
	.space	4
z:
	.space	4
