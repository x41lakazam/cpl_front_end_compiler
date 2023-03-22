Compile CPL code into quadruples intermediate code (to give to a back end compiler)

To compile a CPL file, run `python compile.py path/to/cpl_file`.  
The quad code will be generated in a file called "outfile.quad"


### How it works

1- The lexer first generate tokens based on the CPL grammar, it is defined in `lexer.py`
2- The parser defined in `parser.py` generate an AST of tokens, each token is a custom type defined in `models.py`  
3- The transformer defined in `transformer.py` transform this AST into quadruple code, following simple logic, some special variables 
are inserted during this transformation and are replaced later, they are marked with a % symbol at the beginning, 
for example %+OFFSET is replaced by the line <line-no + OFFSET>


When a syntax/parsing error is detected, an error will be thrown, the parser will continue to parse the next statements
and throw other errors if there are.

### Example of compiling this CPL code:
```
a, b: float;

{
    input(a);
    input(b);

    b = static_cast<int> (a) + b;
    
    switch (a+b){
        case 1:
            a = 1;
            output(a);
        case 2:
            a = 2;
            output(a);
        case 3:
            a = 3;
            output(a);
            break;
        default:
            a = 10;
            output(a);
    }

    if (a>5+b) {
        b = b+5;
        a = b;
        output(b);
    }
    else {
        b = b +3;
        output(a);
    }

    while (a+b>3){
        a = 1;
        break;
        b = 2;
    }
}
```

Output:

```
1:	RINP a
2:	RINP b
3:	RTOI t0 a
4:	IADD t1 t0 b
5:	IASN b t1
6:	IADD t2 a b
7:	IEQL t3 t2 1
8:	JMPZ t3 10
9:	IASN a 1
10:	IPRT a
11:	IEQL t4 t2 2
12:	JMPZ t4 14
13:	IASN a 2
14:	IPRT a
15:	IEQL t5 t2 3
16:	JMPZ t5 19
17:	IASN a 3
18:	IPRT a
19:	JUMP 21
20:	IASN a 10
21:	IPRT a
22:	IADD t7 5 b
23:	IGRT t8 a t7
24:	JMPZ t8 29
25:	IADD t9 b 5
26:	IASN b t9
27:	IASN a b
28:	IPRT b
29:	JUMP 32
30:	IADD t10 b 3
31:	IASN b t10
32:	IPRT a
33:	IADD t11 a b
34:	ITOR t12 3
35:	IGRT t13 t11 t12
36:	JMPZ t13 40
37:	IASN a 1
38:	JUMP 40
39:	IASN b 2
40:	JUMP 32
41:	HALT
```