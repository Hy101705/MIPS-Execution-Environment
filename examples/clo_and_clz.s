	# Some tests of `clo` and `clz`.

main:
	# $ra = -16779279 = 0xfefff7f1
	#     = 0b11111110111111111111011111110001
	# which has 7 leading one bits
	li	$ra, -16779279

	li	$v0, 1
	clo	$a0, $ra
	syscall

	li	$v0, 11
	li	$a0, ','
	syscall

	# $t6 = 2130704369 = 0x7efff7f1
	#     = 0b01111110111111111111011111110001
	# which has 0 leading one bits
	li	$t6, 2130704369

	li	$v0, 1
	clo	$a0, $t6
	syscall

	li	$v0, 11
	li	$a0, ','
	syscall

	# $ra = -1 = 0xffffffff
	#     = 0b11111111111111111111111111111111
	# which has 32 leading one bits
	li	$ra, -1

	li	$v0, 1
	clo	$a0, $ra
	syscall

	li	$v0, 11
	li	$a0, ','
	syscall

	# $ra = 0 = 0x00000000
	#     = 0b00000000000000000000000000000000
	# which has 0 leading one bits
	li	$ra, 0

	li	$v0, 1
	clo	$a0, $ra
	syscall

	li	$v0, 11
	li	$a0, '\n'
	syscall

	# $ra = -16779279 = 0xfefff7f1
	#     = 0b11111110111111111111011111110001
	# which has 0 leading zero bits
	li	$ra, -16779279

	li	$v0, 1
	clz	$a0, $ra
	syscall

	li	$v0, 11
	li	$a0, ','
	syscall

	# $t6 = 2130704369 = 0x7efff7f1
	#     = 0b01111110111111111111011111110001
	# which has 1 leading zero bit
	li	$t6, 2130704369

	li	$v0, 1
	clz	$a0, $t6
	syscall

	li	$v0, 11
	li	$a0, ','
	syscall

	# $ra = -1 = 0xffffffff
	#     = 0b11111111111111111111111111111111
	# which has 0 leading zero bits
	li	$ra, -1

	li	$v0, 1
	clz	$a0, $ra
	syscall

	li	$v0, 11
	li	$a0, ','
	syscall

	# $ra = 0 = 0x00000000
	#     = 0b00000000000000000000000000000000
	# which has 32 leading zero bits
	li	$ra, 0

	li	$v0, 1
	clz	$a0, $ra
	syscall

	li	$v0, 11
	li	$a0, '\n'
	syscall

	li	$v0, 10
	syscall

