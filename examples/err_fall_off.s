main:
	li	$v0, 11
	li	$a0, ':'
	syscall

	li	$a0, '('
	syscall

	li	$a0, '\n'
	syscall

	li	$v0, 10
	# oops... no exit syscall!
	# this is an error.
