	# The $zero ($0) register should always be zero

main:
	# printf("%d", $zero);
	addi	$a0, $zero, 0
	addi	$v0, $zero, 1
	syscall

	# putchar('\n');
	addi	$a0, '\n'
	addi	$v0, $zero, 11
	syscall

	# attempt to change $zero
	addi	$zero, $a0, 1234

	# printf("%d", $zero);
	addi	$a0, $zero, 0
	addi	$v0, $zero, 1
	syscall

	# putchar('\n');
	addi	$a0, '\n'
	addi	$v0, $zero, 11
	syscall

	addi	$v0, $zero, 10
	syscall
