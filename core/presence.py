from pypresence import Presence
import time

client_id = "1314396619445108807"
RPC = Presence(client_id)

RPC.connect()

RPC.update(
    state="Im making this for Celestia! | Presence",
    large_image="test",
    buttons=[{"label": "Check out Celestia!", "url": "https://socials.lat"}]

)
while True:
    time.sleep(60)