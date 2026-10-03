	# Print "hi\n" using only addi and the print_character and exit syscalls

main:
	# putchar('h');
	addi	$v0, $zero, 11
	addi	$a0, $zero, 'h'
	syscall

	# putchar('i');
	addi	$v0, $zero, 11
	addi	$a0, $zero, 'i'
	syscall

	# putchar('\n');
	addi	$v0, $zero, 11
	addi	$a0, $zero, '\n'
	syscall

	# exit(0);
	addi	$v0, $zero, 10
	syscall

