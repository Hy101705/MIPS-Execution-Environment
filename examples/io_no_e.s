	EOF = -1

done:
	# exit(0);
	li	$v0, 10
	syscall

main:
	# int ch = getchar();
	li	$v0, 12
	syscall

	# if (ch == EOF) break;
	beq	$v0, EOF, done
	# if (ch == 'e') continue;
	beq	$v0, 'e', main

	# putchar(ch);
	move	$a0, $v0
	li	$v0, 11
	syscall

	b	main
