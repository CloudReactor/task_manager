import React from 'react';
import Button from '@mui/material/Button';
import makeStyles from '@mui/styles/makeStyles';

interface Props {
	uuid: string;
  handleStopStart: (uuid: string, type: string) => void;
  type: string;
  disabled: boolean;
}

const useStyles = makeStyles(theme => ({
  buttonMargin: {    
    marginLeft: '5px',   
    marginRight: '5px',   
  },
}));

const ButtonStopStart = ({handleStopStart, uuid, type, disabled}: Props) => {
  const classes = useStyles();

	if (type === "stop") {
		return (
			<Button
				size="small"
				variant="outlined"
				color="primary"
				disabled={disabled}
				onClick={() => handleStopStart(uuid, type)}
				className={classes.buttonMargin}
			>
				<i className="fas fa-stop pl-2 pr-2"/>
				Stop
			</Button>
		)
	} else {
		return (
			<Button
				size="small"
				variant="outlined"
				color="primary"
				disabled={disabled}
				onClick={() => handleStopStart(uuid, type)}
				className={classes.buttonMargin}
			>
				<i className="fas fa-play pl-2 pr-2"/>
				Start
			</Button>
		)
	}
};

export default ButtonStopStart;