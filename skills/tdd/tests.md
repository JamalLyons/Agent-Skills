# Good and Bad Tests

## Good Tests

**Integration-style**: Test through the interface that exposes the chosen behavior, using real collaborators where practical.

```typescript
// GOOD: Tests observable behavior
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

Characteristics:

- Tests behavior users/callers care about
- Uses the relevant caller or boundary interface
- Survives internal refactors
- Describes WHAT, not HOW
- One coherent behavior per test; several assertions may establish that behavior

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```typescript
// BAD when calling this internal method is not part of the contract
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

Red flags when they do not observe the selected behavioral contract:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Using a side channel that does not establish the promised behavior

```typescript
// Weak application-level test: persistence alone does not prove retrievability
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// GOOD: Verifies through interface
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

These are contextual judgments, not assertion-syntax bans. A migration test should query the real test database to establish constraints and compatibility. A delivery test may assert that retrying the same idempotency key produces one external charge, and an integration protocol may require one boundary operation before another. Use a recording boundary adapter when appropriate; do not assert private helper calls that callers do not depend on. When real database behavior is the contract, an in-memory fake alone cannot verify it.

**Tautological tests**: Expected value restates the implementation, so the test passes by construction.

```typescript
// BAD: Expected value is recomputed the way the code computes it
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// GOOD: Expected value is an independent, known literal
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```
