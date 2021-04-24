# cursewords

`cursewords` is a "graphical" command line program for solving crossword puzzles in the terminal. It can be used to open files saved in the widely used AcrossLite `.puz` format.

<img src="https://raw.githubusercontent.com/thisisparker/cursewords/master/demo.gif" width=450px>

`cursewords` includes nearly every major feature you might expect in a crossword program, including:

* intuitive navigation
* answer-checking for squares, words, and full puzzles
* a pausable puzzle timer
* a puzzle completeness notification

`cursewords` also includes features for solving puzzles on a Twitch stream with audience interactivity:

* animated rewards for when a user guesses a word
* a chatbot command to request the clue of a given word be posted to the chat

Cursewords is currently under active development, and should not be considered fully "released." That said, it is stable and suitable for everyday use.

## Installation

`cursewords` is only compatible with `python3`, and can be installed through `pip`. If you don't know what that means, the best command is probably:

```bash
pip3 install --user cursewords
```

You should then be ready to go. You can then use  `cursewords` to open `.puz` files directly:

```
cursewords todaysnyt.puz
```

## Usage

If you've used a program to solve crossword puzzles, navigation should be pretty intuitive. `tab` and `shift+tab` are the workhorses for navigation between blanks. `page up` and `page down` (on Mac, `Fn+` up/down arrow keys) jump between words without considering blank spaces. `ctrl+g`, followed by a number, will jump directly to the space with that number.

If you need some help, `ctrl+c` will check the current square, word, or entire puzzle for errors, and `ctrl+r` will reveal answers (subject to the same scoping options). To clear all entries on the puzzle, use `ctrl+x`, and to reset the puzzle to its original state (resetting the timer and removing any stored information about hints and corrections, use `ctrl+z`.

To open a puzzle in `downs-only` mode, where only the down clues are visible, use the `--downs-only` flag when opening the file on the command line.


## Configuration

You can configure the behavior of `cursewords` using command-line options or a configuration file. The configuration file must be named `cursewords.toml`, and can reside in either the directory where you run the `cursewords` command or in `$HOME/.config/`. See the `cursewords.toml` file included with this distribution for example settings.

Settings settable by the configuration file can be overridden on the command line, like so:

```
cursewords --log-to-file --twitch.channel=PuzzleCity todaysnyt.puz
```

True/false settings, like `log-to-file`, are set as flags. `--log-to-file` sets the `log_to_file` option to `true`. To override a flag to `false`, prepend the name with `no-`, as in `--no-log-to-file`.

Settings in TOML sections use the section name followed by a dot, as in `--twitch.channel=...`.


## Twitch integration

`cursewords` includes features for live-streaming puzzle solving on Twitch with audience interactivity. You can connect `cursewords` to the channel's chat room using a bot account or your own account. Features include:

* **Guessing**
  * When someone posts a message to the chat containing a solution to an unsolved clue, the board will highlight the squares. This signals to the solver that someone has made a correct guess, and rewards viewers for guessing.
  * Any word or phrase in a chat message counts as a guess.
* **Clues**
  * Anyone can request one of the clues from the board with the `!clue` command, like so: `!clue 22d` Cursewords posts the requested clue to the room.

These features can be enabled or disabled separately with configuration.

To enable Twitch integration:

1. Create a Twitch.tv account for the bot, or use an existing account that you control.
2. In your browser, visit [https://twitchapps.com/tmi/] and sign in with the bot's account and password. This generates an OAuth token, a string of letters and numbers that begins `oauth:...` Copy the OAuth token to your clipboard.
3. Copy the `cursewords.toml` file from this distribution to the desired location, and edit it to set the parameters under `[twitch]`:
    * `enable = true` : enables the Twitch features
    * `nickname = "..."` : the bot's Twitch account name
    * `channel = "..."` : the name of the Twitch channel (without the `#`)
    * `oauth_token = "oauth:..."` : the OAuth token
    * `enable_guessing = true` : enables the guessing feature
    * `enable_clue = true` : enables the clue command

When you run `cursewords`, it will attempt to connect to the Twitch chat room. You should see the bot account arrive in the room and announce its presence.

### About OAuth tokens

The OAuth token is a temporary password that `cursewords` uses to connect to Twitch with the given account. It is *not* the account password. The OAuth token allows you to grant access to `cursewords` without telling it the real account password.

Keep the OAuth token a secret! It behaves like a real password for accessing the Twitch API. If you no longer want an app to be able to connect using the token, you can revoke access. Sign in to Twitch.tv with the bot account, go to **Settings**, then select the **Connections** tab. Locate the "Twitch Developer" connection then click **Disconnect**.

You can generate a new OAuth token at any time by visiting: [https://twitchapps.com/tmi/]

(There are nicer ways to [authenticate a bot on Twitch](https://dev.twitch.tv/docs/authentication), but Cursewords does not yet support them. Contributions welcome!)

### Troubleshooting

**The bot account does not join the room when I run `cursewords`.**
Verify that configuration parameters are set correctly, and that the configuration file is named `cursewords.toml` and is in either the current working directory or in: `$HOME/.config/`

Occasionally `cursewords` will simply fail to connect to Twitch. Quit (Ctrl-Q) and re-run `cursewords` to try again.

**The bot does not animate a correct guess posted by a user.**
Check that the `enable_guessing` configuration parameter is set to `true` (`--twitch.enable-guessing` on the command line). The bot will invite users to post guesses to the chat when it joins if this feature is enabled correctly.

Check that the word is not already solved on the board. The guessing feature will only animate squares of a correct guess if the word is unsolved, incompletely solved, or solved incorrectly.

A guess can be run together (`DOUBLERAINBOW`) or separated by spaces (`DOUBLE RAINBOW`), and case doesn't matter (`double raIN bOW`). It must start and end at a "word boundary:" `corporeous`, `oreodontoid`, or `choreo` will not match `oreo`. Punctuation cannot appear in the middle of the guess: `o-r-e-o` will not match.

**The bot never replies to the `!clue` command.**
Check that the `enable_clue` configuration parameter is set to `true` (`--twitch.enable-clue` on the command line). The bot will invite users to use the `!clue` command when it joins if this feature is enabled correctly.

Check that `!clue` (an exclamation point followed by the word "clue") is the first word in the chat message.

**The bot replies to the `!clue` command sometimes, but not always.**
To prevent a user from cluttering the chat with clues, each user is restricted to one `!clue` per period of time. This period is configurable using the `clue_cooldown_per_person` parameter (`--twitch.clue-cooldown-per-person` on the command line). The bot will ignore clue commands from a user within this time.

If a single user requests the same clue twice in succession and the bot hasn't spoken since the previous time, Twitch will prevent the bot from posting the same message twice in a row.
