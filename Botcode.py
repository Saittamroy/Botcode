import random
import time
import operator
from highrise import BaseBot 
from highrise.models import SessionMetadata, User, Position
from highrise import __main__
from asyncio import run as arun
import asyncio

class MathGameBot(BaseBot):
    async def on_start(self, session_metadata: SessionMetadata) -> None:
        print("hi im alive?")

        self.highrise.tg.create_task(self.highrise.teleport(
            session_metadata.user_id, Position(6, 0, 2, "FrontRight")))
      
    async def on_user_join(self, user: User) -> None:
        print(f"{user.username} has joined the room")
        await self.highrise.chat(f"{user.username} Welcome to MathQuiz, !help to know more") 

        # check if the user sent the !start command to start the game
    #async def on_chat(self, user: User, message: str) -> None:      
        #if #user.m
            #await self.math_quiz(user)
    async def start_game(self, user: User) -> None:
        await self.highrise.chat(f"Let's start the game, {user.username}!")
        self.scoreboard = {user.id: 0}
        self.lock = asyncio.Lock()
        await self.math_quiz(user) 

    async def math_quiz(self, user: User):
        # generate two random numbers between 1 and 10
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 19)

        # generate a random operator (+, -, or *)
        operator_dict = {"+": operator.add, "-": operator.sub, "*": operator.mul}
        operator_str = random.choice(list(operator_dict.keys()))
        operation = operator_dict[operator_str]

        # calculate the correct answer
        self.answer = operation(num1, num2)

        # ask the user the math question
        await self.highrise.chat(f"*＊✿❀QUESTION❀✿＊* What is »»————>   »  {num1} {operator_str} {num2} ? «")

          
          
    async def score(self, user: User, message: str) -> None:
        await self.highrise.chat(f"{user.username}, your score is {self.scoreboard[user.id]}.")

    #async def on_chat(self, user: User, message: str) -> None:
    async def on_chat(self, user: User, message: str) -> None:
        print(f"{user.username} said: {message}")      
      #print(f"{user.username} has joined the room")
        if message.startswith("!help"):
           await self.highrise.chat("             Start the game»»————> !start,                                           Know your score »»————> !score ")
           return

        if message.startswith("!score"):
            await self.score(user, message)
            return 
        if message.startswith("!start"):
            self.scoreboard = {user.id: 0} # initialize user's score to 0
            #await self.highrise.chat(f"{user.username}, the math game is starting now!")
        
        # check if the message is a valid answer
          
            await self.start_game(user)
            return 
          
        try:
            user_answer = int(message)
        except ValueError:
            return

      # if message.startswith('!start'):
            #await self.math_quiz(user)      
        # check if the user's answer is correct
        async with self.lock:
          if user_answer == self.answer:
        
            await self.highrise.chat(f"❃.✮:▹❀CORRECT❀◃:✮.❃, {user.username}! You got 2 points.")
            self.scoreboard[user.id] += 2
            #await self.score(user, message)
           # await self.show_scores()
            await self.math_quiz(user)
          else:
            await self.highrise.chat(f"Sorry,Wrongಥ_ಥ {user.username}, correct answer is {self.answer}.")
            await self.math_quiz(user)    
          
    async def run(self, room_id, token) -> None:
        await __main__.main(self, room_id, token)

if __name__ == "__main__":
    room_id = "6031f61f562bc94adfe45c85"
    token  = "fb628984143e90b9ee940653e29872e4e82f941715d0a14c1e341baf9fdffca6"
    arun(MathGameBot().run(room_id, token))
