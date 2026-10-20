---
kgnote_schema: "<workspace-schema>"
kgnote_source_id: "<source-id>"
kgnote_source_sha256: "<source-sha256>"
kgnote_generated: true
---

# How a browser reaches a local service

This lesson follows how a browser reaches a service running on a laptop: the application first needs a network connection, the host is identified by an IP address, the service is selected through a port/service endpoint, and the browser exchanges an HTTP request and response.

> [!question] Learning goal
> How does a browser reach the intended local service and get a result back?

## Learning path

1. Establish the network path.
2. Identify the host.
3. Select the service.
4. Send the HTTP request.
5. Read the HTTP response and status code.

→ [[Source/network-path|Start reading the original material]]

## Key concepts

- [[Concepts/IP address|IP address]] — identifies the host in this material.
- [[Concepts/network connection|network connection]] — required before the application exchanges data.
- [[Concepts/HTTP request|HTTP request]] — the request sent as part of the exchange.
- [[Concepts/Port|Port]] — maps to the service endpoint in this simplified example.
- [[Concepts/service endpoint|service endpoint]] — the endpoint selected by the port.
- [[Concepts/HTTP response|HTTP response]] — the response returned to the browser.
- [[Concepts/status code|status code]] — appears with the HTTP response in the result.

## Key relationships

- [[Concepts/HTTP request|HTTP request]] **requires** [[Concepts/network connection|network connection]].
- [[Concepts/Port|Port]] **maps to** [[Concepts/service endpoint|service endpoint]].
- [[Concepts/HTTP response|HTTP response]] and [[Concepts/status code|status code]] are mentioned together, but this source does not establish a more precise relationship.

## Continue

[[Continue Here|Continue from where you left off]]

## My notes

[[My Notes]]

> [!info]- KGnote details
> Generated learning workspace.
> Detailed provenance and review information is available here only when needed.
