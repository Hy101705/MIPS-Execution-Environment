main:
	addi	$t0, $zero, 4242
	addi	$t1, $zero, 0x5f1

	add	$a0, $t0, $t1
	addi	$v0, $zero, 1
	syscall

	addi	$a0, $zero, '\n'
	addi	$v0, $zero, 11
	syscall

	addi	$v0, $zero, 10
	syscall
