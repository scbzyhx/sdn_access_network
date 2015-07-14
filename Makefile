.PHONY: run 
.PHONY: clean
.PHONY: debug

run: ; ryu-manager RestRequestAPI
debug: ; ryu-manager --enable-debugger RestRequestAPI
clean: ;  rm *.pyc

