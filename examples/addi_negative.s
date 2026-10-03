	# try addi with a negative immediate
main:
	# printf("%d", 50 - 8);
	addi	$a0, $zero, 50
	addi	$a0, $a0, -8
	addi	$v0, $zero, 1
	syscall

	# putchar('\n');
	addi	$a0, '\n'
	addi	$v0, $zero, 11
	syscall


	addi	$v0, $zero, 10
	syscall
