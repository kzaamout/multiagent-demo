# Missing price

Scenario: one item required by the drawings is absent from supplier-prices.csv.
Planted defect: remove exit signs (or another clearly required item) from the fixture.
Expected behaviour: Pricing lists the item in its exceptions; the Writer discloses it as an unpriced exclusion; the Reviewer records a minor finding; run passes.
Expected exit: reviewer_pass, retry count 0, one minor finding at Handoff.
Presenter note: shows that gaps surface honestly rather than being invented.
