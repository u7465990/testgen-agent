package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_withdraw_Dbl_Test_Boundary_7 {


    @Test
    public void withdrawWithZeroAmountThrowsIllegalArgumentException() {
        BankAccount account = new BankAccount("test", 100.0);

        try {
            account.withdraw(0.0);
            Assert.fail("Expected IllegalArgumentException for zero amount");
        } catch (IllegalArgumentException expected) {
            Assert.assertEquals("Withdrawal must be positive", expected.getMessage());
        }
    }

}
