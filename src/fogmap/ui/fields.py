"""The controls a settings dialog is built out of, one setting to a field.

   Each field puts itself into three cells of a shared grid sizer - its label,
   the control, and whatever wants the width left over - so that a column of
   them lines up however many there are and whatever kind they are.  They all
   answer to GetValue, SetValue and Enable, and call a handler when the GM
   changes them."""
import wx


# Room to breathe between the three cells of a field.
HGAP = 8
VGAP = 6

# Enough slider to be worth dragging, whatever the label in front of it is.
SLIDER_WIDTH = 180

# Enough box for a number and a sign.
SPIN_WIDTH = 70


class NumericField(object):
	"""A number that can be typed, stepped, or dragged.

	   A slider on its own is quick to sweep and hopeless for setting an exact
	   number, which is what a grid measured off a scanned map needs.  This
	   pairs a spin control - a text box with its own up and down arrows - with
	   a slider over the same value, so either way of setting it is to hand and
	   they always agree."""

	def __init__(self, parent, sizer, label, value, minValue, maxValue,
				 step=1, tip="", onChange=None):
		self.minValue = minValue
		self.maxValue = maxValue
		self.step = step
		self.onChange = onChange
		self.value = self.snap(value)
		# Set while one control is being brought into line with the other, so
		# that doing so does not read back as the GM changing it again.
		self.syncing = False

		self.label = wx.StaticText(parent, -1, "%s:" % label)
		self.spin = wx.SpinCtrl(parent, -1, str(self.value),
								min=minValue, max=maxValue, initial=self.value,
								style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER)
		if (hasattr(self.spin, "SetIncrement")):
			self.spin.SetIncrement(step)
		self.spin.Bind(wx.EVT_SPINCTRL, self.__onSpin)
		# Typing counts as it is typed, so a number that is never finished off
		# with Enter still takes - a dialog is as likely to be left by its OK
		# button as by tabbing out of the box.  What is typed is left alone
		# while it is being typed, though: see __onText.
		self.spin.Bind(wx.EVT_TEXT, self.__onText)
		self.spin.Bind(wx.EVT_TEXT_ENTER, self.__onDone)
		self.spin.Bind(wx.EVT_KILL_FOCUS, self.__onDone)
		# On macOS a spin control is a text box and a pair of arrows in a box
		# of their own rather than one native control, and it is the text box
		# inside that the keyboard is really in: a focus event there is not
		# passed out to its parent, so the one that matters is bound here too.
		for child in self.spin.GetChildren():
			if (isinstance(child, wx.TextCtrl)):
				child.Bind(wx.EVT_KILL_FOCUS, self.__onDone)

		self.slider = wx.Slider(parent, -1, self.value, minValue, maxValue,
								size=(SLIDER_WIDTH, -1), style=wx.SL_HORIZONTAL)
		self.slider.SetLineSize(step)
		self.slider.SetPageSize(step * 10)
		self.slider.Bind(wx.EVT_SLIDER, self.__onSlider)

		if (tip):
			for window in (self.label, self.spin, self.slider):
				window.SetToolTip(tip)

		# A fixed width on the box, so that a column of fields does not go
		# ragged where one of them happens to take a minus sign.
		self.spin.SetMinSize((SPIN_WIDTH, -1))

		sizer.Add(self.label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		sizer.Add(self.spin, 0, wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.slider, 1, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

	def snap(self, value):
		"""The nearest value this field will take: in range, and on a step
		   boundary counted up from the minimum.  A slider does not know about
		   steps and a text box will take anything at all, so both go through
		   here."""
		value = max(self.minValue, min(self.maxValue, int(value)))
		steps = int(round((value - self.minValue) / float(self.step)))
		return min(self.minValue + (steps * self.step), self.maxValue)

	def GetValue(self):
		return self.value

	def SetValue(self, value):
		"""Put a value in from outside, without calling the handler back."""
		self.__setValue(value, notify=False)

	def SetRange(self, minValue, maxValue):
		"""Move the range this field will take, for one that is only allowed as
		   far as some other setting says - and pull the value in after it if
		   it no longer fits."""
		if ((minValue, maxValue) == (self.minValue, self.maxValue)):
			return
		self.minValue, self.maxValue = minValue, maxValue
		self.syncing = True
		self.spin.SetRange(minValue, maxValue)
		self.slider.SetRange(minValue, maxValue)
		self.syncing = False
		self.SetValue(self.value)

	def Enable(self, enable=True):
		for window in (self.label, self.spin, self.slider):
			window.Enable(enable)

	def __setValue(self, value, notify=True, setSpin=True):
		value = self.snap(value)
		changed = (value != self.value)
		self.value = value
		self.syncing = True
		if (setSpin and (self.spin.GetValue() != value)):
			self.spin.SetValue(value)
		if (self.slider.GetValue() != value):
			self.slider.SetValue(value)
		self.syncing = False
		if (changed and notify and (self.onChange != None)):
			self.onChange(value)

	def __readSpin(self):
		try:
			return int(self.spin.GetTextValue().strip())
		except ValueError:
			return self.spin.GetValue()

	def __onSpin(self, evt):
		evt.Skip()
		if (not self.syncing):
			self.__setValue(self.__readSpin())

	def __onText(self, evt):
		evt.Skip()
		if (self.syncing):
			return
		try:
			value = int(self.spin.GetTextValue().strip())
		except ValueError:
			# An empty box, or half a number on its way to being one: a minus
			# sign arrives on its own.
			return
		# The box itself is deliberately left as it was typed.  Putting the
		# value back into it would rewrite "1" as the smallest the field will
		# take the moment the 1 was pressed, and a GM typing 100 would never
		# get past the first digit.  It is put right on the way out.
		self.__setValue(value, setSpin=False)

	def __onDone(self, evt):
		"""Enter, or the box being left: the number is finished with."""
		# Focus events have to be passed on or the box is left looking focused
		# after the mouse has gone elsewhere.
		evt.Skip()
		if (self.syncing):
			return
		self.__setValue(self.__readSpin())
		# After the control has done whatever it does to itself on the way out,
		# so that what the box ends up showing is what the value actually came
		# to - 5 typed into a field that only goes down to 8, say.
		wx.CallAfter(self.__showValue)

	def __showValue(self):
		if (not self.spin):
			# The dialog was closed between the box being left and this.
			return
		self.syncing = True
		self.spin.SetValue(self.value)
		self.syncing = False

	def __onSlider(self, evt):
		if (not self.syncing):
			self.__setValue(self.slider.GetValue())


class ChoiceField(object):
	"""One of a short list of names, as a drop-down.

	   The control is narrow and the third column is left empty rather than
	   stretched into: a drop-down as wide as a slider looks like a mistake."""

	def __init__(self, parent, sizer, label, value, choices, tip="",
				 onChange=None):
		self.choices = tuple(choices)
		self.onChange = onChange
		self.value = value if (value in self.choices) else self.choices[0]

		self.label = wx.StaticText(parent, -1, "%s:" % label)
		self.choice = wx.Choice(parent, -1, choices=list(self.choices))
		self.choice.SetStringSelection(self.value)
		self.choice.Bind(wx.EVT_CHOICE, self.__onChoice)

		if (tip):
			for window in (self.label, self.choice):
				window.SetToolTip(tip)

		sizer.Add(self.label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		sizer.Add(self.choice, 0, wx.ALIGN_CENTER_VERTICAL)
		sizer.Add((0, 0))

	def GetValue(self):
		return self.value

	def SetValue(self, value):
		"""Put a value in from outside, without calling the handler back."""
		if (value not in self.choices):
			return
		self.value = value
		self.choice.SetStringSelection(value)

	def Enable(self, enable=True):
		for window in (self.label, self.choice):
			window.Enable(enable)

	def __onChoice(self, evt):
		value = self.choice.GetStringSelection()
		if (value == self.value):
			return
		self.value = value
		if (self.onChange != None):
			self.onChange(value)


class FlagField(object):
	"""On or off, as a checkbox.

	   The caption goes in the label column like every other field's rather
	   than on the checkbox itself, so that a column of settings still reads
	   down the same line whatever sort each of them is."""

	def __init__(self, parent, sizer, label, value, tip="", onChange=None):
		self.onChange = onChange
		self.value = bool(value)

		self.label = wx.StaticText(parent, -1, "%s:" % label)
		self.check = wx.CheckBox(parent, -1, "")
		self.check.SetValue(self.value)
		self.check.Bind(wx.EVT_CHECKBOX, self.__onCheck)

		if (tip):
			for window in (self.label, self.check):
				window.SetToolTip(tip)

		sizer.Add(self.label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		sizer.Add(self.check, 0, wx.ALIGN_CENTER_VERTICAL)
		sizer.Add((0, 0))

	def GetValue(self):
		return self.value

	def SetValue(self, value):
		"""Put a value in from outside, without calling the handler back."""
		self.value = bool(value)
		self.check.SetValue(self.value)

	def Enable(self, enable=True):
		for window in (self.label, self.check):
			window.Enable(enable)

	def __onCheck(self, evt):
		self.value = self.check.GetValue()
		if (self.onChange != None):
			self.onChange(self.value)
