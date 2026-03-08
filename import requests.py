import requests

# 【重要】Beds24の画面で「Generate invite code」を押して出た6桁程度のコードを入れてください
INVITE_CODE = "6lMmsk7PKZlPFzG5IipGwLjSNh1ZCM9CEvhdM8dKOnTa+X+cHbq0Pui/PsrN3otNdIqlIlzR51jJXczM0o8PWiGLSBY6iuMMeU9BQ8arkv73fp8wXCOafuMil5RHRAlTvcEMDUEYnef6OeSpw15b3w==" 

url = "https://beds24.com/api/v2/authentication/setup"
headers = {
    "accept": "application/json",
    "code": INVITE_CODE
}

try:
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if response.status_code == 200:
        print("成功しました！")
        print(f"あなたの Refresh Token は: {data.get('refreshToken')}")
        print("\nこのTokenは大切に保管し、人には教えないでください。")
    else:
        print(f"エラーが発生しました: {data}")
except Exception as e:
    print(f"通信エラー: {e}")