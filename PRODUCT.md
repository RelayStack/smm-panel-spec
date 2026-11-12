# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: static HTML + CSS + a single vanilla-JS file, served by GitHub Pages from `docs/`. The
whole project is dependency-free by design and the demo must not be the exception; a build step
would be the only moving part in a repository whose pitch is that there is nothing to install.

## Users

SMM panel operators and the developers who integrate with them: resellers running a storefront on
top of several panels, and backend engineers at a panel wiring up the reseller API. They arrive from
a GitHub search, a package registry, or a forum thread, usually mid-task, often fixing an
integration that broke after a panel changed a response shape.

## Product Purpose

The SMM Panel API is the form-encoded, action-based format that panels and reseller tools speak. It
is universally implemented and nowhere specified, so every integration re-derives it and each panel
diverges in the same three places. This repository writes the format down, ships a read-only
conformance tester that answers "does this panel actually work", and gives a mock to build against.
Success is a developer who stops guessing and starts testing.

## Positioning

The spec and the tester, not another client. Three client libraries already exist and are
commodity; nothing documents the format or lets you verify an implementation against it. The
conformance tester is the part a neighbouring project cannot copy-paste, because it encodes the
divergences rather than the happy path.

## Operating Context

Developers work in a terminal, against a panel they may not administer, holding an API key that is
a bearer credential for real money. They cannot afford writes against someone else's account, so
every check the tool performs is read-only by contract. They compare several panels when choosing a
provider and run the same check in their own CI afterwards.

## Capabilities and Constraints

- Read-only conformance probes: `services`, `balance`, and an error-envelope probe using an
  impossible order id. The tool never places an order and never changes state.
- Prose spec plus a machine-readable JSON spec.
- A mock panel that advances orders pending → inprogress → completed.
- Reference clients in Python, PHP and Node, all dependency-free.
- Runs on the Python standard library; CI covers 3.12 and 3.13.
- No accounts, no telemetry, no cookies, nothing stored.

## Brand Commitments

Plain, technical, evidence-first. No marketing adjectives, no invented benchmarks, no claims about
delivery quality. Everything the page asserts is reproducible with one command from the repository.

## Evidence on Hand

- `SPEC.md` and `spec/smm-panel-api.json` — the normative format.
- `conformance/smmcheck.py` — the tester, with real captured output from a run against the mock.
- `tests/test_conformance.py` — asserts the checker passes the mock and rejects a wrong-shaped panel.
- Real terminal output in the README, reproducible locally.
- Absent, must not be fabricated: customer counts, star counts, benchmark rankings, testimonials,
  pricing, and any claim that a named real panel is compliant.

## Product Principles

1. Show the tool working, not a description of the tool.
2. Read-only is a promise the page makes explicit, because the visitor's key spends money.
3. Every number on the page is a number the visitor can produce in one command.
4. The format is the product; clients are examples.

## Accessibility & Inclusion

Static HTML with real semantics, keyboard-reachable controls, visible focus, and contrast that
survives the dark palette. No motion that cannot be disabled by `prefers-reduced-motion`.
