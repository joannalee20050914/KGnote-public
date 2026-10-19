# BitePacer 驅動的迷你計網：從 Client／Server 到 ngrok

最開始只要這個：

```text
程式 A                         程式 B
Client                         Server

「我要 /liff/diet」
      ───────────────────────→

      ←───────────────────────
                    「好，這是結果」
```

**Client**：主動提出 request 的一方。
**Server**：等待 request，處理後回 response 的一方。

注意它們不是固定的「電腦種類」。你的 Chrome、LINE server 或 `curl` 都可以當 client。

## 它怎麼找到 Flask？

需要兩個概念：

```text
IP / hostname → 找「哪台機器」
port          → 找「那台機器上的哪個網路服務」
```

因此 `127.0.0.1:5050` 可以拆成：

```text
127.0.0.1  :  5050
    ↑            ↑
哪台主機       哪個入口
```

`127.0.0.1` 是特殊的 loopback address，指向「自己這台主機」。

```text
http://127.0.0.1:5050/liff/diet

http://       → 用 HTTP 溝通
127.0.0.1    → 跟自己這台 Mac 溝通
:5050        → 找 listening 在 port 5050 的程式
/liff/diet   → 跟 Web application 要這個 resource/route
```

## HTTP 與 Flask

```text
Client
    │ HTTP Request：GET /liff/diet
    ▼
Flask
    │ Python 處理
    │ HTTP Response：200 OK
    ▼
Client
```

看到 `@app.route("/liff/diet")` 時，可以理解成：Flask 收到 request 後查看 routing table，找到這個 path 對應的 Python function，執行 handler，再生成 response。

## 為什麼需要 ngrok？

LINE 不能直接 request `http://127.0.0.1:5050`，因為 LINE server 的 `127.0.0.1` 代表 LINE server 自己，不是你的 Mac。

```text
Internet
   ↓
https://xxxx.ngrok.app
   ↓
ngrok tunnel
   ↓
你的 Mac :5050
   ↓
Flask
```

ngrok 補上外界通往 Mac 本機 Flask 的路徑。

---

來源：摘錄自 product owner 與 ChatGPT 的 BitePacer 教學對話，原始對話日期 2026-08-14。此檔保留本次產品測試需要的完整教學上下文，不代表整篇原始對話。
