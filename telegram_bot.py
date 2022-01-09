import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.ext import Filters, Updater, Dispatcher, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext
from telegram.error import InvalidToken
from enum import Enum, auto

from config import TG_BOT_TOKEN
from solitaire_game import Game, InvalidMoveError, icons
from telegram_user import TelegramUser

class Button(Enum):
    DRAW_CARD: auto = auto()
    PLAY_AGAIN: auto = auto()

# start bot by instantiating TelegramBot and calling it's start() method
class TelegramBot:
    """ Singleton class representing the telegram bot. """
    updater: Updater
    users: dict[int, TelegramUser] = dict()

    @property
    def buttons_markup(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("Draw Card", callback_data = Button.DRAW_CARD.value),
            InlineKeyboardButton("Play Again", callback_data = Button.PLAY_AGAIN.value),
        ]])

    def __init__(self) -> None:
        """ Initialize stuff. """
        # set up updater, dispatcher, and logging
        logging.basicConfig(format = '%(asctime)s - %(levelname)s - %(message)s', level = logging.INFO)
        try:
            self.updater = Updater(token = TG_BOT_TOKEN, use_context = True)
        except InvalidToken:
            logging.error("Enter your telegram bot access token into config.py TG_BOT_TOKEN variable first!")
            exit()
        # set up and register handlers
        # NOTE: command handlers by default also trigger when a command is edited
        # NOTE: in that case, update.message == None, so we need to use update.effective_message instead
        handlers = [
            CommandHandler('start', self.cmd_start),
            CommandHandler('move', self.cmd_move),
            CommandHandler('help', self.cmd_help),
            CommandHandler('cheat', self.cmd_cheat),
            CallbackQueryHandler(self.button_callback),
            MessageHandler(Filters.command, self.unknown_command),
        ]
        for handler in handlers:
            self.updater.dispatcher.add_handler(handler)

    def start_bot(self) -> None:
        """ Start telegram bot. """
        # start telegram bot
        self.updater.start_polling()
        # run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
        self.updater.idle()

    def get_telegram_user(self, effective_user: User) -> TelegramUser:
        """ Get telegram user with id=<user_id> if exists, else create it. """
        if effective_user.id in self.users.keys():
            return self.users[effective_user.id]
        else:
            logging.info(f"Adding user {effective_user.full_name} to 'users' dict.")
            tg_user = TelegramUser(effective_user = effective_user, game = None)
            self.users[effective_user.id] = tg_user
            return tg_user

    def log_action(self, tg_user: TelegramUser, message: str, severity: int = logging.INFO) -> None:
        """ Log user action. """
        logging.log(level=severity, msg=f"({tg_user.full_name}) {message}")

    def button_callback(self, update: Update, context: CallbackContext) -> None:
        """ Parses the CallbackQuery and updates the message text. """
        user = self.get_telegram_user(update.effective_user)
        query = update.callback_query
        button_pressed = int(query.data)
        try:
            if button_pressed == Button.DRAW_CARD.value:
                self.log_action(user, "Draw card")
                user.game.draw_card()
            elif button_pressed == Button.PLAY_AGAIN.value:
                self.log_action(user, "Play again")
                user.game = Game()
            else:
                logging.error("Invalid button.")
                query.answer(text = "Invalid button.", show_alert = True)
                return
        except AttributeError:
            # if Draw Card is pressed before game starts
            logging.error("Stale game.")
            query.answer(text="Game is stale. Type '/start' or press 'Play Again' to start a new game.", show_alert=True)
            return
        finally:
            # CallbackQueries need to be answered, even if no notification to the user is needed
            # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
            query.answer()

        query.edit_message_text(text=str(user.game), reply_markup=self.buttons_markup)

    def cmd_start(self, update: Update, context: CallbackContext) -> None:
        """
            Start the game.
            Syntax: /start
        """
        # start new game by creating instance of Game
        user = self.get_telegram_user(update.effective_user)
        self.log_action(user, update.effective_message.text)
        user.game = Game()
        update.effective_message.reply_text(text=str(user.game), reply_markup=self.buttons_markup)

    def cmd_move(self, update: Update, context: CallbackContext) -> None:
        """
            Move a card and all cards before it to another row.
            Syntax: /move <from_row> <card_index> <to_row>
        """
        user = self.get_telegram_user(update.effective_user)
        args = context.args
        self.log_action(user, update.effective_message.text)
        try:
            user.game.move_card(int(args[0]), int(args[2]), int(args[1]))
        except InvalidMoveError as e:
            strf_exc = f"{type(e).__name__}: {e}"
            logging.error(strf_exc)
            update.effective_message.reply_text(text=strf_exc)
        # check for game termination
        if user.game.check_game_over() is True:
            logging.info(f"Victory for {user.full_name}!")
            update.effective_message.reply_text(text = str(user.game), reply_markup = self.buttons_markup)
            update.effective_message.reply_text(text = f"{icons.BLING}Congratulations, you win!{icons.BLING}")
            user.game = None  # disallow changing game state after it ends
            return
        update.effective_message.reply_text(text=str(user.game), reply_markup=self.buttons_markup)

    def cmd_help(self, update: Update, context: CallbackContext) -> None:
        """
            Print the syntax for each command.
            Syntax: /help
        """
        user = self.get_telegram_user(update.effective_user)
        self.log_action(user, update.effective_message.text)
        help_text = "\n".join([
            "/start",
            "/move <from_row> <card_index> <to_row>",
            "/cheat",
            "/help",
        ])
        update.effective_message.reply_text(help_text)

    def cmd_cheat(self, update: Update, context: CallbackContext) -> None:
        """ Cheat for testing purposes. """
        user = self.get_telegram_user(update.effective_user)
        self.log_action(user, update.effective_message.text)
        try:
            user.game.cheat()
            update.effective_message.reply_text(text=str(user.game), reply_markup=self.buttons_markup)
        except AttributeError:
            logging.error("Game hasn't started yet.")
            update.effective_message.reply_text(text="Game hasn't started yet. Type /start to start a new game.")

    def unknown_command(self, update: Update, context: CallbackContext) -> None:
        """ Handle unknown commands. """
        user = self.get_telegram_user(update.effective_user)
        self.log_action(user, update.effective_message.text, logging.ERROR)
        logging.error(f"Unknown command.")
        context.bot.send_message(
                chat_id = update.effective_chat.id,
                text = "Unknown command. Type /help for a list of commands.",
        )

if __name__ == '__main__':
    TelegramBot().start_bot()
