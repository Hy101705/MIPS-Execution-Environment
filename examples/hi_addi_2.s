	# The first 'x' should not be printed since
	# the entry_point (determined by the position of
	# the main label) is equal to 3, so execution
	# starts at the printing of the `h`.

	# putchar('x');
	addi	$v0, $zero, 11
	addi	$a0, $zero, 'x'
	syscall

main:
	# putchar('h');
	addi	$v0, $zero, 11
	addi	$a0, $zero, 'h'
	syscall

	# putchar('e');
	addi	$v0, $zero, 11
	addi	$a0, $zero, 'e'
	syscall

	# putchar('y');
	addi	$v0, $zero, 11
	addi	$a0, $zero, 'y'
	syscall

	# putchar('\n');
	addi	$v0, $zero, 11
	addi	$a0, $zero, '\n'
	syscall

	# exit(0);
	addi	$v0, $zero, 10
	syscall

	# The program has exited.. so this 'z' shouldn't be printed
	# putchar('z');
	addi	$v0, $zero, 11
	addi	$a0, $zero, 'z'
	syscall
