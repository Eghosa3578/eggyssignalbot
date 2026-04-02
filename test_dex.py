import asyncio
import httpx
import json

async def test():
    async with httpx.AsyncClient() as client:
        # Get boosted tokens
        r1 = await client.get("https://api.dexscreener.com/token-boosts/latest/v1")
        if r1.status_code == 200:
            boosts = r1.json()
            sol_addresses = [p["tokenAddress"] for p in boosts if p.get("chainId") == "solana"][:30]
            print(f"Found {len(sol_addresses)} solana addresses.")
            
            if sol_addresses:
                addr_str = ",".join(sol_addresses)
                r2 = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr_str}")
                print("Status Code:", r2.status_code)
                if r2.status_code == 200:
                    pairs = r2.json().get("pairs", [])
                    print("Got pairs:", len(pairs))
                    if pairs:
                        print(json.dumps(pairs[0]))
                else:
                    print("Error:", r2.text)

asyncio.run(test())
