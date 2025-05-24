#!/usr/bin/env python3
"""Test script to debug Java file parsing issues."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tree_sitter_languages import get_language, get_parser
import time


def test_java_parsing():
    # Test small Java file (like the failing ones)
    small_content = """package net.theorcs.model.enums;

public enum SystemPropertyCategory {
    SECURITY,
    EMAIL,
    STORAGE,
    LOGGING,
    RECAPTCHA
}"""

    # Test larger Java file content (like successful ones)
    large_content = """package net.theorcs.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;

@Configuration
public class SecurityConfig {
    
    public void configure(HttpSecurity http) throws Exception {
        http.authorizeRequests()
            .antMatchers("/public/**").permitAll()
            .anyRequest().authenticated();
    }
    
    // More methods here...
}"""

    try:
        parser = get_parser("java")
        print("Tree-sitter Java parser loaded successfully")

        # Test small file
        print("\n=== Testing Small Java File ===")
        start = time.time()
        tree = parser.parse(small_content.encode("utf-8"))
        end = time.time()
        print(f"Small Java file parsed in {(end-start)*1000:.2f}ms")
        print(f"Root node: {tree.root_node}")
        print(f"Root node type: {tree.root_node.type}")
        print(f"Child count: {tree.root_node.child_count}")

        # Walk the tree
        cursor = tree.walk()
        node_count = [0]  # Use list to avoid global issues

        def count_nodes(cursor):
            node_count[0] += 1
            if cursor.goto_first_child():
                count_nodes(cursor)
                while cursor.goto_next_sibling():
                    count_nodes(cursor)
                cursor.goto_parent()

        count_nodes(cursor)
        print(f"Total nodes: {node_count[0]}")

        # Test large file
        print("\n=== Testing Large Java File ===")
        start = time.time()
        tree2 = parser.parse(large_content.encode("utf-8"))
        end = time.time()
        print(f"Large Java file parsed in {(end-start)*1000:.2f}ms")
        print(f"Root node: {tree2.root_node}")
        print(f"Root node type: {tree2.root_node.type}")
        print(f"Child count: {tree2.root_node.child_count}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_java_parsing()
