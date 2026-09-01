# Architecture

Core data flow: repository scanner → Tree-sitter/AST symbol extraction → symbol chunks → lexical+dense indices → RRF fusion → reranking → deterministic NetworkX graph → bounded graph expansion → impact report → optional workspace patch → sandbox tests/static checks → verification → human approval.

Graph edges are deterministic/static and store relationship type, confidence, and extraction method. Dynamic Python dispatch is a known limitation and should be evaluated rather than hidden.
