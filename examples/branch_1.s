main:
	li	$v0, 1
	li	$a0, 32
	li	$t0, 33

	beq	$a0, $t0, exit
	addi	$a0, $a0, 1
	beq	$a0, $t0, skip

	addi	$a0, $a0, 2
	addi	$a0, $a0, 3

skip:
	addi	$a0, $a0, 4
	addi	$a0, $a0, 5

	syscall

	li	$v0, 11
	li	$a0, '\n'
	syscall

exit:
	move	$v0, $a0
	syscall
