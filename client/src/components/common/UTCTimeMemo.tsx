import moment from 'moment';
import React, {Component, Fragment } from 'react';
import styles from './UTCTimeMemo.module.scss';

interface Props {
}

interface State {
	currentTimeString: string | null;
	interval: any;
}

class UTCTimeMemo extends Component<Props, State> {
	constructor(props: Props) {
		super(props);

		this.state = {
			currentTimeString: null,
			interval: null
		};
	}

	componentDidMount(): void {
		const interval = setInterval(this.refreshTime, 500);

		this.setState({
			interval
		});
	}

	componentWillUnmount(): void {
		if (this.state.interval) {
			clearInterval(this.state.interval);
		}
	}

	refreshTime = (): void => {
		this.setState({
			 currentTimeString: moment().utc().format( 'Y-MM-DD HH:mm')
		})
	}

	public render() {
		return (
			<p className={styles.timeMemo}>
				All times in UTC.
				{
					this.state.currentTimeString &&
					<Fragment>&nbsp;Current UTC time is { this.state.currentTimeString }.</Fragment>
				}
			</p>
		);
	}
};

export default UTCTimeMemo;