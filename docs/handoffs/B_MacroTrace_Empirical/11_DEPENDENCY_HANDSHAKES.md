# Role B Dependency Handshakes

## Needs from A

DataResolve contract, endpoint, successful dataset fixture and error fixtures.

## Receives from C

ToolRequest and timeout policy.

## Delivers to C

EvidenceBundle COMPLETE, PARTIAL and FAILED fixtures, followed by real Bundle.

## Delivers to D

Research Graph artifact URL through C or a frozen read-only route. D cannot depend on MacroTrace internal classes.
