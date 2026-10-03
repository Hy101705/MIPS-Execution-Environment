main:
	la	$t0, x
	lw	$t1, 0($t0)
	lw	$t2, 4($t0)
	add	$t3, $t1, $t2		# x[2] = x[0] + x[1];
	sw	$t3, 8($t0)

	li	$v0, 1			# syscall 1: print_int
	lw	$a0, 8($t0)		#
	syscall				# printf("%d", x[2]);

	li	$v0, 11			# syscall 11: print_char
	li	$a0, '\n'		#
	syscall				# putchar('\n');

	li	$v0, 10
	syscall

	.data

x:	.word 17, 25, 0			# int x[] = {17, 25, 0}
