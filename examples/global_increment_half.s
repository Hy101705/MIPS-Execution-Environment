	.text
main:
	# Locals:
	# - $t0: copy of global_counter

	lh	$t1, global_counter
	addi	$t1, $t1, 1
	lh	$t1, global_counter	# global_counter = global_counter + 1;

	li	$v0, 1			# syscall 1: print_int
	la	$t0, global_counter	#
	lh	$a0, 0($t0)
	syscall				# printf("%d", global_counter);

	li	$v0, 11			# syscall 11: print_char
	li	$a0, '\n'
	syscall				# putchar('\n');

	li	$v0, 10
	syscall

	.data
global_counter:
	.word	0xabff
