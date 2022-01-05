import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, Dispatcher, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext
from enum import Enum, auto
from typing import Optional

from config import TG_BOT_TOKEN
from solitaire_game import Game, InvalidMoveError, icons

class Button(Enum):
    DRAW_CARD: auto = auto()
    PLAY_AGAIN: auto = auto()

# start bot by instantiating TelegramBot and calling it's start() method
class TelegramBot:
    updater: Updater
    game: Optional[Game]
    buttons_markup: InlineKeyboardMarkup = InlineKeyboardMarkup([[
        InlineKeyboardButton("Draw Card", callback_data = Button.DRAW_CARD.value),
        InlineKeyboardButton("Play Again", callback_data = Button.PLAY_AGAIN.value),
    ]])

    def __init__(self) -> None:
        """ Initialize stuff. """
        # set up updater, dispatcher, and logging
        self.updater = Updater(token = TG_BOT_TOKEN, use_context = True)
        logging.basicConfig(format = '%(asctime)s - %(levelname)s - %(message)s', level = logging.INFO)
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

    def button_callback(self, update: Update, context: CallbackContext) -> None:
        """ Parses the CallbackQuery and updates the message text. """
        query = update.callback_query

        button_pressed = int(query.data)
        try:
            if button_pressed == Button.DRAW_CARD.value:
                self.game.draw_card()
            elif button_pressed == Button.PLAY_AGAIN.value:
                self.game = Game()
            else:
                query.answer(text = "Invalid button.", show_alert = True)
                logging.error("Invalid button.")
                return
        except AttributeError:
            # if Draw Card is pressed before game starts
            query.answer(text="Game is stale. Type '/start' or press 'Play Again' to start a new game.", show_alert=True)
            logging.error("Stale game.")
            return
        finally:
            # CallbackQueries need to be answered, even if no notification to the user is needed
            # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
            query.answer()

        query.edit_message_text(text=str(self.game), reply_markup=self.buttons_markup)

    def cmd_start(self, update: Update, context: CallbackContext) -> None:
        """
            Start the game.
            Syntax: /start
        """
        # start new game by creating instance of Game
        self.game = Game()
        update.effective_message.reply_text(text=str(self.game), reply_markup=self.buttons_markup)

    def cmd_move(self, update: Update, context: CallbackContext) -> None:
        """
            Move a card and all cards before it to another row.
            Syntax: /move <from_row> <card_index> <to_row>
        """
        args = context.args
        try:
            self.game.move_card(int(args[0]), int(args[2]), int(args[1]))
        except InvalidMoveError as e:
            strf_exc = f"{type(e).__name__}: {e}"
            logging.error(strf_exc)
            update.effective_message.reply_text(text=strf_exc)
        # check for game termination
        if self.game.check_game_over() is True:
            update.effective_message.reply_text(text = str(self.game), reply_markup = self.buttons_markup)
            update.effective_message.reply_text(text = f"{icons.BLING}Congratulations, you win!{icons.BLING}")
            self.game = None
            return
        update.effective_message.reply_text(text=str(self.game), reply_markup=self.buttons_markup)

    def cmd_help(self, update: Update, context: CallbackContext) -> None:
        """
            Print the syntax for each command.
            Syntax: /help
        """
        help_text = "\n".join([
            "/start",
            "/move <from_row> <card_index> <to_row>",
            "/cheat",
            "/help",
        ])
        update.effective_message.reply_text(help_text)

    def cmd_cheat(self, update: Update, context: CallbackContext) -> None:
        """ Cheat for testing purposes. """
        try:
            self.game.cheat()
            update.effective_message.reply_text(text=str(self.game), reply_markup=self.buttons_markup)
        except AttributeError:
            update.effective_message.reply_text(text="Game hasn't started yet. Type /start to start a new game.")

    def unknown_command(self, update: Update, context: CallbackContext) -> None:
        """ Handle unknown commands. """
        context.bot.send_message(
                chat_id = update.effective_chat.id,
                text = "Unknown command. Type /help for a list of commands.",
        )

if __name__ == '__main__':
    TelegramBot().start_bot()
