main:
	la	$t0, my_string
loop:
	lb	$t1, 3($t0)
	beqz	$t1, print

	addiu	$t1, $t1, -7
	sb	$t1, 3($t0)

	addiu	$t0, $t0, 1
	b	loop

print:
	la	$a0, my_string
	li	$v0, 4
	syscall

	li	$v0, 10
	syscall

	.data
my_string:
	.ascii	"Helsv'~vysk('Jvunyh{z'vu'nl{{pun'z{ypun'wypu{pun'~vyrpun'A7"
	.byte	17, 0
