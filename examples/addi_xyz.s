
	# putchar('!');
	addi	$v0, $zero, 11
	addi	$a0, $zero, '!'
	syscall

main:
	# putchar('x');
	addi	$v0, $zero, 11
	addi	$a0, $v0, 109
	syscall

	# putchar('y');
	addi	$a0, $a0, 1
	syscall

	# putchar('z');
	addi	$a0, $a0, 1
	syscall

	# putchar('\n');
	addi	$a0, $a0, -112
	syscall

	# exit(0);
	addi	$v0, $a0, 0
	syscall
