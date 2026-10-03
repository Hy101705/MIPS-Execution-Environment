	.text
main:

	li	$t0, 42			#
	sw	$t0, g			# g = 42;

	li	$v0, 1			# syscall 1: print_int
	la	$t0, g			#
	lw	$a0, 0($t0)		#
	syscall				# printf("%d", g);

	li	$v0, 10
	syscall

	.data

a:
	.word	16			# int a = 16;
b:
	.space	4			# int b;
c:
	.space	4			# char c[4];
d:
	.byte	1, 2, 3, 4		# char d[4] = {1, 2, 3, 4};
e:
	.byte	0:4			# char e[4] = {0, 0, 0, 0};
f:
	.asciiz	"hello"			# char *f = "hello";
	.align	2
g:
	.space	4			# int g;
