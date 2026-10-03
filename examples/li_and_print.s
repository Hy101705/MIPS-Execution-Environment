main:
	# printf("%d", 4242);
	li	$a0, 4242
	li	$v0, 1
	syscall

	# putchar(' ');
	li	$v0, 1
	li	$a0, ' '
	syscall

	# printf("%d", 0xe826a2);
	li	$a0, 0xe826a2
	li	$v0, 1
	syscall

	# putchar(' ');
	li	$v0, 1
	li	$a0, ' '
	syscall

	# printf("%d", 0xabcddcba);
	li	$a0, 0xabcddcba
	li	$v0, 1
	syscall

	# putchar(' ');
	li	$v0, 1
	li	$a0, '\n'
	syscall

	# exit(0);
	li	$v0, 10
	syscall
