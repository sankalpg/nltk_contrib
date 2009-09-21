"""
Module for tokenizing and parsing s-expressions
"""
import nltk
import re
import os


from statemachine import PushDownMachine

class SexpList(list):
    """
    A list, extracted from an s-expressoin string. The open and 
    closin gparentheses used by the list are strong in L{lparen} and 
    L{rparen}, respectively. Assuming this C{SexpList} was generated by 
    parsing a string, its istem will all be either strings or nested 
    C{SexpList}s.
    """
    
    def __init__(self, lparen, rparen, values=()):
        """
        Initialize and return the object.

        @param lparen: The style of left parenthesis to use for this list
        @type lparen: string
        @param rparen: The style of right parenthesis to use for this list
        @type rparen: string
        @param values: The values the the list should contain
        @type values: Tuple
        """

        # left (open) parenthesis
        self.lparen = lparen
        # right (close) parenthesis
        self.rparen = rparen

    def pp(self):
        s = self.lparen
        for i, val in enumerate(self):
            if isinstance(val, SexpList):
                s += val.pp()
            elif isinstance(val, basestring):
                s += val
            else:
                s += repr(val)
            if i < len(self)-1:
                s += ' '
        return s + self.rparen

    def __repr__(self):
        """
        Returns the string representation of this list

        @return: The string representation of the list
        """
        return '<SexpList: %s>' % self.pp()


class SexpListParser(object):
    """
    Parse the text and return a a C{SexpList}
    """

    def __init__(self):
        """
        Create and return the object
        """

        self.machine = PushDownMachine()
        self.tokenizer = None

        # set up the parenthesis
        self.parens = {'(':')', '[':']', '{':'}'}
        self.lparens = self.parens.keys()
        self.rparens = self.parens.values()
        self._build_machine()
        self.machine.stack = [[]]
    
    def _build_machine(self):
        """
        Build the state machine with the defined states
        """
        self.machine.addstate(self._lparen)
        self.machine.addstate(self._rparen)
        self.machine.addstate(self._word)
        self.machine.addstate(self._end, end_state=True)
        self.machine.setstart(self._lparen)

    def _tokenizer(self, to_tokenize):
        """
        Return a tokenizer
        """
        lparen_res = ''.join([re.escape(lparen) for lparen in self.parens.keys()])
        rparen_res = ''.join([re.escape(rparen) for rparen in self.parens.values()])

        tok_re = re.compile('[%s]|[%s]|[^%s%s\s]+' %
                            (lparen_res, rparen_res, lparen_res, rparen_res))
    
        return tok_re.finditer(to_tokenize)

    def parse(self, to_parse):
        """
        Parse the text and return the C{SexpList}

        @param to_parse: The string to parse
        @type to_parse: string
        @return: list of lists 
        """

        self.tokenizer = self._tokenizer(SexpListParser.remove_comments(to_parse))
        start = self.tokenizer.next().group()
        if (start not in self.lparens):
            raise ValueError("Expression must start with an open paren")
        stack_w_list = self.machine.run(tokens=start)
        return stack_w_list[0][0]
    

    def _transition(self):
        """
        Move to the next state based on the following token
        """
        try:
            tok = self.tokenizer.next().group()
            # collect strings
            if tok.startswith('"') and tok.endswith('"'):
                tok = tok[1:-1]
            elif tok.startswith('"') and not tok.endswith('"'):
                while True:
                    tok = "%s %s" % (tok, self.tokenizer.next().group())
                    if tok.endswith('"'):
                        tok = tok.replace('"', '')
                        break
        except Exception:
            return self._end, ""
        
        if tok in self.lparens:
            return self._lparen, tok
        elif tok in self.rparens:
            return self._rparen, tok
        return self._word, tok

    def _lparen(self, current):
        """
        Actions to take given the left parenthesis
        """
        self.machine.push(SexpList(current, self.parens[current]))
        return self._transition()
        

    def _rparen(self, current):
        """
        Actions to take given the right parenthesis
        """
        if len(self.machine.stack) == 1:
            raise ValueError("Unexpected close paren")
        if current != self.machine.stack[-1].rparen:
            raise ValueError("Mismatched paren")
        # close the and make it an item of the previous list
        closed_sexp_list = self.machine.stack.pop()
        # this makes sure that we dont add any of the tracing stuff 
        if not any(i in closed_sexp_list for i in ("control-demo", "control", ":demo", "trace")):
            self.machine.stack[-1].append(closed_sexp_list)
        return self._transition()

    def _word(self, current):
        """
        Actions to take given that the current token is a word
        """
        # add the word to the last list
        if len(self.machine.stack) == 0:
            raise ValueError("Expected open paren")
        if not ('%' in current):
            self.machine.stack[-1].append(current)
        return self._transition()

    def _end(self, token):
        """
        Actions to take when the string is finished processing
        """
        if len(self.machine.stack) > 1:
            raise ValueError("Expected close paren")
        assert len(self.machine.stack) == 1
        if len(self.machine.stack[0]) == 0:
            raise ValueError("Excepted open paren")
        if len(self.machine.stack[0]) > 1:
            raise ValueError("Expected a single sexp list")

        return self.machine.stack[0][0]

    @staticmethod
    def _error(s, match):
        pos = match.start()
        for lineno, line in enumerate(s.splitlines(True)):
            if pos < len(line): break
            pos -= len(line)
        return 'line %s, char %s' % (lineno+1, pos)

    @staticmethod
    def remove_comments(text):
        """
        Remove the comments from a given expression
        """
        remover = re.compile("\;.*")
        result = []
        for line in text.splitlines(True):
            temp = remover.sub('', line)
            if not temp.isspace():
                result.append(temp)
        return "".join(result)
    
class SexpFileParser(object):
    """
    Parse a file that contains multiple s-expressions
    """

    def __init__(self, filename):
        """
        Construct and return the object
        """
        self.sfile = filename

        # The SexpListParser parses one expression at a time
        # We wrap the whole file into single expression
        self.source = "(\n%s\n)" % open(self.sfile).read()
        
    def parse(self):
        """
        Parse the file and retun a list of s-expressions

        @return: list of lists
        """

        slp = SexpListParser()
        return slp.parse(self.source)


if __name__ == "__main__":
    # testing SexpListParser
    lines = open('tests/sexp.txt').readlines()
    for test in lines:
        try:
            print '%s' % test
            l = SexpListParser().parse(test)
            print '==>', SexpListParser().parse(test)
            print
        except Exception, e:
            print 'Exception:', e
    
    # testing the SexpFileParser
    sfp = SexpFileParser('tests/typed_gr4.fuf')
    print sfp.parse()



    
    