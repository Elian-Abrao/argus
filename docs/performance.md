# Performance
[Voltar ao indice](README.md)

## Pontos que mais impactam
- Escrita em disco (muitos logs por segundo).
- Formatacao detalhada (verbose alto em DEBUG).
- Envio remoto com lote pequeno.

## Recomendacoes
- Use `batch_size` maior no `remote_sink` quando volume for alto.
- Evite logs muito verbosos no console em producao.
- Em servicos longos, use `server_mode=True` para evitar snapshot inicial.
- Prefira `INFO` para console e `DEBUG` apenas em arquivo.

## Quando investigar
- CPU alta durante picos de logs.
- Latencia grande ao escrever em disco.
- Filas do RabbitMQ crescendo (remote API).
